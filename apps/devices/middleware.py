from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from apps.devices.services import (
    enforce_device_policy_for_service,
    attach_device_cookie,
    DevicePolicyError,
)


class DeviceEnforcementMiddleware:
    """
    Enforce device resolution and policy on every authenticated request.
    Attaches request.device and request.device_new.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip unauthenticated requests
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return self.get_response(request)

        # Respect registry toggle if device identity is disabled
        try:
            from apps.core.models import AppRegistry

            reg = AppRegistry.get_solo()
            if reg and getattr(reg, "device_identity_enabled", True) is False:
                return self.get_response(request)
        except Exception:
            pass

        # Skip for trust/untrust endpoints to avoid consent/fp prompts
        if request.path.startswith(reverse("users:device_approval_needed")):
            return self.get_response(request)

        try:
            ok, ctx = enforce_device_policy_for_service(request, request.user, service_name="request")
            request.device = ctx.get("device")
            request.device_new = ctx.get("is_new", False)
            response = self.get_response(request)
            attach_device_cookie(response, ctx.get("device"))
            if ctx.get("is_new"):
                try:
                    request.session["pending_device_prompt_uuid"] = getattr(ctx.get("device"), "os_fingerprint", None)
                except Exception:
                    pass
                messages.info(request, "New device registered. Approve/trust it to continue using this browser.")
            return response
        except DevicePolicyError as exc:
            reason = exc.reason
            if reason == "device_key_required":
                messages.error(request, "Device fingerprint is required. Refresh the page to register this device.")
                return redirect("users:devices")
            if reason in {"untrusted_new_device", "mfa_required", "mfa_required_risk"}:
                messages.error(request, "New device requires approval or MFA.")
                return redirect("users:device_approval_needed")
            if reason in {"device_quota_exceeded", "limit_reached", "user_window_quota", "monthly_device_quota", "yearly_device_quota"}:
                messages.error(request, "Device limit reached. Remove an old device to continue.")
                return redirect("users:device_eviction")
            if reason == "blocked_device":
                messages.error(request, "This device is blocked. Contact support.")
                return redirect("users:devices")
            messages.error(request, "Device not allowed for this action.")
            return redirect("users:devices")


class DevicePayloadMiddleware:
    """
    Attach device payload captured via JS to the request for downstream fingerprinting.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            request.device_payload = request.session.get("device_payload")
        except Exception:
            request.device_payload = None
        return self.get_response(request)
