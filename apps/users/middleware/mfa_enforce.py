
from __future__ import annotations

from typing import Iterable

from django.shortcuts import redirect
from django.urls import resolve, reverse


class EnforceMfaMiddleware:
    """
    Enforce MFA when UsersSettings.require_mfa is enabled.

    - Skips static/admin/api/consent paths.
    - Applies only to authenticated users.
    - Redirects to email verification when MFA is required and the user is unverified.
    """

    SAFE_URL_NAMES: Iterable[str] = {
        "account_login",
        "account_logout",
        "account_signup",
        "users:verify_email",
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
        self.verify_email_url = reverse("users:verify_email")

    def __call__(self, request):
        user = getattr(request, "user", None)

        try:
            from apps.users.models import UsersSettings

            us = UsersSettings.get_solo()
            require_mfa = bool(getattr(us, "require_mfa", False))
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

        if require_mfa and not getattr(user, "email_verified_at", None):
            return redirect(self.verify_email_url)

        return self.get_response(request)


