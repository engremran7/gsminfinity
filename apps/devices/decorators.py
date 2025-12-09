
from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.devices.services import (
    enforce_device_policy_for_login,
    enforce_device_policy_for_service,
    DevicePolicyError,
)


def audit_device_event(event_type: str = "login") -> Callable:
    """
    Decorator for login success handlers to enforce device policy and attach request.device.
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs):
            user = getattr(request, "user", None)
            try:
                _, ctx = enforce_device_policy_for_login(request, user)
                setattr(request, "device", ctx.get("device"))
            except DevicePolicyError as exc:
                return JsonResponse({"ok": False, "reason": exc.reason}, status=403)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def require_registered_device(service_name: str, redirect_url: Optional[str] = None) -> Callable:
    """
    Decorator for sensitive views to enforce device policy.
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args, **kwargs):
            user = getattr(request, "user", None)
            if not user or not getattr(user, "is_authenticated", False):
                return redirect(redirect_url or reverse("account_login"))

            try:
                _, ctx = enforce_device_policy_for_service(request, user, service_name)
                setattr(request, "device", ctx.get("device"))
            except DevicePolicyError as exc:
                return JsonResponse({"ok": False, "reason": exc.reason}, status=403)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


