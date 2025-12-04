from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.devices.models import Device, DeviceEvent


@staff_member_required
def admin_placeholder(request: HttpRequest) -> HttpResponse:
    return HttpResponse("Devices admin placeholder", content_type="text/plain")


@login_required
def my_devices(request: HttpRequest) -> HttpResponse:
    devices = Device.objects.filter(user=request.user).order_by("-last_seen")[:20]
    return render(request, "devices/my_devices.html", {"devices": devices})


@staff_member_required
def device_events(request: HttpRequest) -> HttpResponse:
    events = DeviceEvent.objects.select_related("device").order_by("-created_at")[:50]
    return render(request, "devices/events.html", {"events": events})
