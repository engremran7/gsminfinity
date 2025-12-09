from __future__ import annotations

import json
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

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
@csrf_exempt
def device_payload_view(request: HttpRequest) -> JsonResponse:
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
    return JsonResponse({"ok": True})
