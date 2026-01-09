from __future__ import annotations

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.devices.models import Device, DeviceEvent
from apps.devices.utils.device_fingerprint import make_os_fingerprint


@staff_member_required(login_url="admin_suite:admin_suite_login")
def admin_placeholder(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Devices admin placeholder", content_type="text/plain")


@login_required
def my_devices(request: HttpRequest) -> HttpResponse:
    devices = Device.objects.filter(user=request.user).order_by("-last_seen_at")[:20]
    return render(request, "devices/my_devices.html", {"devices": devices})


@staff_member_required(login_url="admin_suite:admin_suite_login")
def device_events(request: HttpRequest) -> HttpResponse:
    events = DeviceEvent.objects.select_related("device").order_by("-created_at")[:50]
    return render(request, "devices/events.html", {"events": events})


# ---------------------------------------------------------------------
# Device payload API (collect JS fingerprint and store in session)
# ---------------------------------------------------------------------


@require_POST
@csrf_protect
def device_payload_view(request: HttpRequest) -> JsonResponse:
    """
    Collect device fingerprint data from JS and store in session.
    SECURITY: Requires CSRF token to prevent malicious fingerprint injection.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    allowed = {
        "screen",
        "pixel_ratio",
        "timezone",
        "cores",
        "device_memory",
        "touch_points",
        "languages",
        "gpu_vendor",
        "gpu_renderer",
    }
    clean = {k: data.get(k, "") for k in allowed}
    request.session["device_payload"] = clean
    request.session.modified = True

    # -----------------------------------------------------------------
    # Fix for "Creating a lot of devices" / Duplication
    # -----------------------------------------------------------------
    # If a device was created during the initial page load (without payload),
    # it has a "Weak" fingerprint. Now that we have the payload, we should
    # migrate that "Weak" device to the "Strong" fingerprint instead of
    # letting the next request create a duplicate "Strong" device.
    if request.user.is_authenticated:
        try:
            ua = request.META.get("HTTP_USER_AGENT", "")
            # 1. Calculate Weak Fingerprint (Empty payload)
            weak_fp, _ = make_os_fingerprint(request.user.id, ua, {})

            # 2. Calculate Strong Fingerprint (With current payload)
            strong_fp, _ = make_os_fingerprint(request.user.id, ua, clean)

            # Only migrate if they are different (i.e., payload actually adds entropy)
            if weak_fp != strong_fp:
                # Find the weak device
                weak_device = Device.objects.filter(
                    user=request.user, os_fingerprint=weak_fp
                ).first()
                strong_device = Device.objects.filter(
                    user=request.user, os_fingerprint=strong_fp
                ).first()

                if weak_device:
                    if not strong_device:
                        # Case 1: Weak exists, Strong does not -> Upgrade Weak to Strong
                        weak_device.os_fingerprint = strong_fp
                        current_meta = (
                            weak_device.metadata
                            if isinstance(weak_device.metadata, dict)
                            else {}
                        )
                        weak_device.metadata = {**current_meta, "payload": clean}
                        weak_device.save(update_fields=["os_fingerprint", "metadata"])
                    else:
                        # Case 2: Both exist (Duplicate scenario) -> Delete Weak, keep Strong
                        # This cleans up the "two devices" issue automatically
                        weak_device.delete()
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(
                f"Device fingerprint migration skipped: {e}"
            )

    return JsonResponse({"ok": True})


@require_POST
@csrf_protect
@login_required
def acknowledge_new_device(request: HttpRequest) -> HttpResponse:
    """
    Register the device as trusted and clear the popup.
    Handles fingerprint upgrades (Weak -> Strong) if payload is available.

    The frontend sends the os_fingerprint from the popup session data,
    which helps us identify the correct device even if fingerprint changed.

    If dismiss_only=true, just mark the popup as shown without trusting the device.
    """
    import logging

    from apps.devices.models import Device
    from apps.devices.services import resolve_or_create_device
    from apps.devices.utils.device_fingerprint import make_os_fingerprint

    logger = logging.getLogger(__name__)

    # Parse request body for os_fingerprint hint from frontend
    frontend_fp = None
    dismiss_only = False
    try:
        data = json.loads(request.body.decode("utf-8"))
        frontend_fp = data.get("os_fingerprint", "").strip()
        dismiss_only = data.get("dismiss_only", False)
    except Exception:
        pass

    # Handle dismiss-only requests (user clicked X to close popup)
    if dismiss_only:
        # Just mark the device as shown so popup doesn't reappear
        if frontend_fp:
            shown_devices = set(request.session.get("devices_popup_shown", []))
            shown_devices.add(frontend_fp)
            request.session["devices_popup_shown"] = list(shown_devices)
        # Clear the popup session data
        for key in ["new_device_popup", "pending_device_prompt_uuid"]:
            if key in request.session:
                del request.session[key]
        request.session.modified = True
        return JsonResponse({"ok": True, "message": "Popup dismissed"})

    # 1. Identify the pending device
    # Priority: frontend fingerprint > session fingerprint
    pending_uuid = frontend_fp or request.session.get("pending_device_prompt_uuid")
    pending_device = None
    if pending_uuid:
        pending_device = Device.objects.filter(
            user=request.user, os_fingerprint=pending_uuid
        ).first()

    # 2. Calculate the current (Strong) fingerprint
    payload = getattr(request, "device_payload", {}) or {}
    ua = request.META.get("HTTP_USER_AGENT", "")
    current_fp, _ = make_os_fingerprint(request.user.id, ua, payload)

    final_device = pending_device

    # 3. Handle fingerprint upgrade scenario (Weak -> Strong)
    if pending_device and pending_device.os_fingerprint != current_fp:
        logger.debug(
            f"Fingerprint mismatch: pending={pending_device.os_fingerprint[:16]}... current={current_fp[:16]}..."
        )

        # Check if the "Strong" device already exists
        strong_device = Device.objects.filter(
            user=request.user, os_fingerprint=current_fp
        ).first()

        if strong_device:
            # Strong device exists. Use it and delete the weak one.
            logger.debug(
                f"Upgrading: deleting weak device {pending_device.id}, using strong device {strong_device.id}"
            )
            pending_device.delete()
            final_device = strong_device
        else:
            # Strong device doesn't exist. Upgrade the pending device's fingerprint.
            logger.debug(f"Upgrading device {pending_device.id} fingerprint to strong")
            pending_device.os_fingerprint = current_fp
            if payload:
                meta = pending_device.metadata or {}
                if isinstance(meta, dict):
                    meta["payload"] = payload
                else:
                    meta = {"payload": payload}
                pending_device.metadata = meta
            pending_device.save(update_fields=["os_fingerprint", "metadata"])
            final_device = pending_device

    # 4. Fallback: If no pending device found, try current fingerprint or resolve/create
    if not final_device:
        # Try to find device by current fingerprint
        final_device = Device.objects.filter(
            user=request.user, os_fingerprint=current_fp
        ).first()

        if not final_device:
            try:
                final_device, _, _ = resolve_or_create_device(
                    request, request.user, service_name="acknowledge"
                )
            except Exception as e:
                logger.warning(f"Failed to resolve/create device: {e}")

    # 5. Trust the final device
    if final_device:
        final_device.is_trusted = True
        final_device.save(update_fields=["is_trusted"])
        logger.info(
            f"Device {final_device.id} marked as trusted for user {request.user.id}"
        )
    else:
        logger.warning(f"No device found to trust for user {request.user.id}")
        return JsonResponse({"ok": False, "error": "Device not found"}, status=400)

    # 6. Clear session flags and mark device as popup-shown
    for key in ["new_device_popup", "pending_device_prompt_uuid"]:
        if key in request.session:
            del request.session[key]

    # Mark this device fingerprint as having been shown popup
    # Prevents the popup from re-appearing for this device
    if final_device:
        shown_devices = set(request.session.get("devices_popup_shown", []))
        shown_devices.add(final_device.os_fingerprint)
        request.session["devices_popup_shown"] = list(shown_devices)

    request.session.modified = True

    return JsonResponse({"ok": True, "message": "Device registered successfully"})
