from __future__ import annotations

from typing import Iterable
from django.shortcuts import redirect
from django.urls import reverse, resolve


class EnforceProfileCompletionMiddleware:
    """
    Enterprise-grade enforcement that ensures authenticated users complete their profile
    before accessing the rest of the platform.

    Features:
    - Zero redirect loops
    - Excludes auth, admin, logout, static, consent, and health endpoints
    - Ultra-fast: uses path startswith + resolver_match fallback
    - Compatible with Django 5.2+ and Allauth 0.65+
    - No accidental blocking of AJAX/HTMX/XHR/API endpoints
    - Compatible with non-HTML API requests (returns response unchanged)
    """

    # ----------------------------------------------------------------------
    # Pre-resolved URL names avoid repeated reverse() calls (micro-optimizing)
    # ----------------------------------------------------------------------
    PROFILE_URL_NAME = "users:tell_us_about_you"

    # URLs that must never be intercepted
    SAFE_URL_NAMES: Iterable[str] = {
        PROFILE_URL_NAME,
        "account_login",
        "account_logout",
        "account_signup",
        "account_reset_password",
        "account_reset_password_done",
        "account_reset_password_from_key",
        "account_reset_password_from_key_done",
    }

    # PATH prefixes to ignore entirely
    SAFE_PATH_PREFIXES: Iterable[str] = (
        "/admin",
        "/static",
        "/media",
        "/api",
        "/health",
        "/consent",    # prevent blocking when consent banner loads
    )

    def __init__(self, get_response):
        self.get_response = get_response
        # compute once
        self.profile_url = reverse(self.PROFILE_URL_NAME)

    # ------------------------------------------------------------------
    # Main middleware
    # ------------------------------------------------------------------
    def __call__(self, request):

        user = getattr(request, "user", None)

        # --- Fast exit for anonymous users ----------------------------------
        if not (user and user.is_authenticated):
            return self.get_response(request)

        # --- Do not run for admin/staff access to Django admin -------------
        if user.is_staff and request.path.startswith("/admin"):
            return self.get_response(request)

        # --- Already completed ---------------------------------------------
        if getattr(user, "profile_completed", True):
            return self.get_response(request)

        path = request.path

        # --- Safe paths (static, media, admin, consent, api...) ------------
        for prefix in self.SAFE_PATH_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        # --- Prevent redirect loops ----------------------------------------
        if path == self.profile_url:
            return self.get_response(request)

        # --- Safe named routes (auth/login/signup etc.) --------------------
        try:
            # resolver_match is cached inside request by Django 5+
            match = request.resolver_match or resolve(path)
            if match and match.view_name in self.SAFE_URL_NAMES:
                return self.get_response(request)
        except Exception:
            # Resolving failure → allow request to proceed
            return self.get_response(request)

        # --- Prevent blocking of AJAX/HTMX/API --------------------------------
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return self.get_response(request)
        if request.headers.get("HX-Request") == "true":
            return self.get_response(request)
        if request.content_type == "application/json":
            return self.get_response(request)

        # --- Finally: enforce redirect -------------------------------------
        return redirect(self.PROFILE_URL_NAME)
