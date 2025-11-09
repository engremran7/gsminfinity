# apps/site_settings/views.py
"""
Site Settings Views
====================
Unified interface for global and tenant-specific configuration access.

✅ Features:
- Per-site caching with unified key pattern
- Robust fallback logic for missing tenant configs
- JSON API for frontend initialization
- Secure verification file serving (strict whitelist)
- Policy page rendering with cache control
"""

import logging
from pathlib import Path
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from .models import SiteSettings, TenantSiteSettings

log = logging.getLogger(__name__)


# ============================================================
#  INTERNAL UTILITY: SETTINGS RESOLVER
# ============================================================
def _get_settings(request=None):
    """
    Retrieve current site settings with robust fallback logic.

    Order of precedence:
      1. TenantSiteSettings for the current site
      2. Global SiteSettings singleton
      3. Dummy fallback with safe defaults
    """

    try:
        # Derive consistent site identifier
        site_domain = "global"
        if request:
            try:
                site_domain = get_current_site(request).domain
            except Exception:
                site_domain = request.get_host()

        # ✅ Unified cache key convention
        cache_key = f"active_site_settings_{site_domain}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Prefer tenant-specific configuration
        try:
            if request:
                current_site = get_current_site(request)
                settings_obj = (
                    TenantSiteSettings.objects.select_related("site")
                    .get(site=current_site)
                )
            else:
                settings_obj = SiteSettings.get_solo()
        except TenantSiteSettings.DoesNotExist:
            log.debug("Tenant settings not found, using global fallback.")
            settings_obj = SiteSettings.get_solo()

        # ✅ Cache site-specific settings
        cache.set(cache_key, settings_obj, timeout=300)
        return settings_obj

    except Exception as exc:
        log.warning("Settings resolver fallback triggered: %s", exc)

        # ✅ Fallback safe defaults
        class DummySettings:
            site_name = "GsmInfinity"
            site_header = "GSM Admin"
            site_description = "Default configuration"
            enable_signup = True
            enable_password_reset = True
            max_login_attempts = 5
            rate_limit_window_seconds = 300
            recaptcha_enabled = False
            enforce_unique_device = False
            max_devices_per_user = 3
            require_mfa = False
            enable_notifications = True
            meta_tags = []
            verification_files = []

        dummy = DummySettings()
        cache.set("active_site_settings_dummy", dummy, timeout=60)
        return dummy


# ============================================================
#  VIEW: SETTINGS DETAIL (ADMIN / DEBUG)
# ============================================================
@require_GET
@cache_page(60 * 5)
def site_settings_view(request):
    """Render a summary of current site/tenant settings for admins or diagnostics."""
    s = _get_settings(request)
    context = {
        "site_settings": s,
        "meta_tags": getattr(s, "meta_tags", []),
        "verification_files": getattr(s, "verification_files", []),
    }
    return render(request, "site_settings/detail.html", context)


# ============================================================
#  API: JSON SETTINGS SNAPSHOT
# ============================================================
@require_GET
@cache_page(60)
def settings_info(request):
    """
    JSON API for frontend initialization, configuration sync, or diagnostics.
    Returns minimal but essential metadata.
    """
    s = _get_settings(request)
    try:
        site_domain = get_current_site(request).domain
    except Exception:
        site_domain = request.get_host()

    data = {
        "site_name": getattr(s, "site_name", "GsmInfinity"),
        "site_header": getattr(s, "site_header", ""),
        "site_description": getattr(s, "site_description", ""),
        "site_domain": site_domain,
        "enable_signup": getattr(s, "enable_signup", True),
        "enable_password_reset": getattr(s, "enable_password_reset", True),
        "recaptcha_enabled": getattr(s, "recaptcha_enabled", False),
        "require_mfa": getattr(s, "require_mfa", False),
        "max_login_attempts": getattr(s, "max_login_attempts", 5),
        "rate_limit_window_seconds": getattr(s, "rate_limit_window_seconds", 300),
    }
    return JsonResponse(data, json_dumps_params={"indent": 2})


# ============================================================
#  PUBLIC: VERIFICATION FILE SERVING
# ============================================================
@require_GET
def verification_file(request, filename):
    """
    Serve uploaded verification files for domain ownership validation.

    ✅ Strict extension whitelist (.html, .txt)
    ✅ Prevents path traversal attacks
    """
    s = _get_settings(request)
    try:
        safe_name = Path(filename).name  # neutralize traversal attempts
        file_obj = s.verification_files.get(file__iendswith=safe_name)

        allowed_ext = (".html", ".txt")
        file_name = file_obj.file.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_ext):
            log.warning("Blocked invalid verification file type: %s", safe_name)
            raise ValueError("Invalid verification file type")

        return redirect(file_obj.file.url)

    except Exception as exc:
        log.error("Verification file error [%s]: %s", filename, exc)
        raise Http404("Verification file not found or invalid type")


# ============================================================
#  PUBLIC POLICY PAGES
# ============================================================
@require_GET
@cache_page(60 * 10)
def privacy_policy(request):
    """Render the privacy policy page."""
    return render(request, "site_settings/privacy.html", {"site_settings": _get_settings(request)})


@require_GET
@cache_page(60 * 10)
def terms_of_service(request):
    """Render the terms of service page."""
    return render(request, "site_settings/terms.html", {"site_settings": _get_settings(request)})


@require_GET
@cache_page(60 * 10)
def site_verification(request):
    """Render verification resources page (meta tags + file links)."""
    return render(request, "site_settings/verification.html", {"site_settings": _get_settings(request)})
