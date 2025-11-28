from __future__ import annotations

from typing import Iterable

from django.shortcuts import redirect
from django.urls import resolve, reverse


class EnforceMfaMiddleware:
    """
    Enforce MFA/device registration when SiteSettings.require_mfa is enabled.

    - Skips static/admin/api/consent paths.
    - Applies only to authenticated users.
    - Redirects to devices page for enrollment.
    """

    SAFE_URL_NAMES: Iterable[str] = {
        "users:devices",
        "account_login",
        "account_logout",
        "account_signup",
    }
    SAFE_PATH_PREFIXES: Iterable[str] = (
        "/admin",
        "/static",
        "/media",
        "/api",
        "/consent",
        "/.well-known",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.devices_url = reverse("users:devices")

    def __call__(self, request):
        user = getattr(request, "user", None)

        try:
            from apps.site_settings.models import SiteSettings

            ss = SiteSettings.get_solo()
            require_mfa = bool(getattr(ss, "require_mfa", False))
        except Exception:
            require_mfa = False

        if not require_mfa or not user or not user.is_authenticated:
            return self.get_response(request)

        path = request.path
        for prefix in self.SAFE_PATH_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        try:
            match = request.resolver_match or resolve(path)
            if match and match.view_name in self.SAFE_URL_NAMES:
                return self.get_response(request)
        except Exception:
            return self.get_response(request)

        # If user has no active device fingerprints, enforce enrollment
        try:
            if not user.device_fingerprints.filter(is_active=True).exists():
                return redirect(self.devices_url)
        except Exception:
            return self.get_response(request)

        return self.get_response(request)
