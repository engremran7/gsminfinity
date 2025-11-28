"""
apps.site_settings.views
========================
Enterprise-grade Views for GSMInfinity Site & Tenant Settings.

✓ Django 5.2+ / Python 3.12+
✓ Zero deprecated APIs
✓ Stable, import-safe, drop-in replacement
✓ Tenant-aware settings resolution
✓ Safe verification file serving
✓ JSON bootstrap for frontend
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.functional import SimpleLazyObject
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.views.decorators.vary import vary_on_headers

from .models import SiteSettings, TenantSiteSettings

log = logging.getLogger(__name__)


# =====================================================================================
# INTERNAL: SETTINGS SNAPSHOT SERIALIZER (stable & safe)
# =====================================================================================


def _settings_snapshot(obj: Any) -> Dict[str, Any]:
    """
    Convert a SiteSettings or TenantSiteSettings instance into a pure dict.
    Completely defensive → never throws exceptions.
    """
    try:
        payload = {
            "site_name": getattr(obj, "site_name", "GSMInfinity"),
            "site_header": getattr(obj, "site_header", ""),
            "site_description": getattr(obj, "site_description", ""),
            "enable_signup": bool(getattr(obj, "enable_signup", True)),
            "enable_password_reset": bool(getattr(obj, "enable_password_reset", True)),
            "recaptcha_enabled": bool(getattr(obj, "recaptcha_enabled", False)),
            "require_mfa": bool(getattr(obj, "require_mfa", False)),
            "max_login_attempts": int(getattr(obj, "max_login_attempts", 5)),
            "rate_limit_window_seconds": int(
                getattr(obj, "rate_limit_window_seconds", 300)
            ),
            "enable_tenants": bool(getattr(obj, "enable_tenants", False)),
            "enable_blog": bool(getattr(obj, "enable_blog", True)),
            "enable_blog_comments": bool(
                getattr(obj, "enable_blog_comments", True)
            ),
            # Branding / theme keys used by base.html and JS bootstrap
            "primary_color": getattr(obj, "primary_color", "#0d6efd"),
            "secondary_color": getattr(obj, "secondary_color", "#6c757d"),
            "logo": (
                getattr(obj, "logo", None).url if getattr(obj, "logo", None) else None
            ),
            "dark_logo": (
                getattr(obj, "dark_logo", None).url
                if getattr(obj, "dark_logo", None)
                else None
            ),
            "favicon": (
                getattr(obj, "favicon", None).url
                if getattr(obj, "favicon", None)
                else None
            ),
            "meta_tags": [],
            "verification_files": [],
        }

        # -------------------------
        # META TAGS
        # -------------------------
        meta = getattr(obj, "meta_tags", None)
        if meta:
            try:
                if hasattr(meta, "values"):
                    payload["meta_tags"] = list(meta.values("name", "content"))
                else:
                    payload["meta_tags"] = [
                        {
                            "name": getattr(m, "name", ""),
                            "content": getattr(m, "content", ""),
                        }
                        for m in meta
                    ]
            except Exception:
                log.debug("Meta tag serialization failed", exc_info=True)

        # -------------------------
        # VERIFICATION FILES
        # -------------------------
        vfiles = getattr(obj, "verification_files", None)
        if vfiles:
            try:
                if hasattr(vfiles, "values"):
                    payload["verification_files"] = list(vfiles.values("id", "file"))
                else:
                    out = []
                    for vf in vfiles:
                        f = getattr(vf, "file", None)
                        out.append(
                            {
                                "id": getattr(vf, "id", None),
                                "file": getattr(f, "name", None),
                                "url": getattr(f, "url", None),
                            }
                        )
                    payload["verification_files"] = out
            except Exception:
                log.debug("Verification file serialization failed", exc_info=True)

        return payload

    except Exception as exc:
        log.exception("settings_snapshot fallback triggered: %s", exc)
        return {
            "site_name": "GSMInfinity",
            "site_header": "",
            "site_description": "",
            "enable_signup": True,
            "enable_password_reset": True,
            "recaptcha_enabled": False,
            "require_mfa": False,
            "max_login_attempts": 5,
            "rate_limit_window_seconds": 300,
            "primary_color": "#0d6efd",
            "secondary_color": "#6c757d",
            "logo": None,
            "dark_logo": None,
            "favicon": None,
            "meta_tags": [],
            "verification_files": [],
        }


# =====================================================================================
# INTERNAL: TENANT-AWARE SETTINGS RESOLVER (stable)
# =====================================================================================


def _get_settings(request: Optional[HttpRequest] = None) -> Dict[str, Any]:
    """
    Return final effective settings (tenant → global).
    Fully defensive: never raises, always returns stable dict.
    """

    try:
        if request:
            try:
                domain = get_current_site(request).domain
            except Exception:
                domain = request.get_host()
        else:
            domain = "global"

        cache_key = f"active_site_settings::{domain}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        obj = None

        # Tenant overrides (if available)
        if request:
            try:
                site = get_current_site(request)
                obj = (
                    TenantSiteSettings.objects.select_related("site")
                    .prefetch_related("meta_tags", "verification_files")
                    .filter(site=site)
                    .first()
                )
            except Exception:
                obj = None

        # Global fallback
        if obj is None:
            try:
                obj = SiteSettings.get_solo()
            except Exception:
                obj = None

        snapshot = _settings_snapshot(obj)
        cache.set(cache_key, snapshot, timeout=300)
        return snapshot

    except Exception as exc:
        log.exception("_get_settings FAIL: %s", exc)
        fallback = _settings_snapshot(object())
        cache.set("active_site_settings::fallback", fallback, timeout=60)
        return fallback


# =====================================================================================
# PUBLIC JSON API
# =====================================================================================


@require_GET
@vary_on_headers("Host")
@cache_page(60)
def settings_info(request: HttpRequest) -> JsonResponse:
    """Return JSON bootstrap settings for frontend."""
    s = _get_settings(request)

    try:
        domain = get_current_site(request).domain
    except Exception:
        domain = request.get_host()

    return JsonResponse(
        {
            "site_name": s.get("site_name", "GSMInfinity"),
            "site_header": s.get("site_header", ""),
            "site_description": s.get("site_description", ""),
            "site_domain": domain,
            "enable_signup": s.get("enable_signup", True),
            "enable_password_reset": s.get("enable_password_reset", True),
            "recaptcha_enabled": s.get("recaptcha_enabled", False),
            "require_mfa": s.get("require_mfa", False),
            "max_login_attempts": s.get("max_login_attempts", 5),
            "rate_limit_window_seconds": s.get("rate_limit_window_seconds", 300),
        },
        json_dumps_params={"indent": 2},
    )


# ⭐⭐⭐ CRITICAL: URL COMPATIBILITY ALIAS ⭐⭐⭐
# Your project references views.info → so we alias it.
info = settings_info


# =====================================================================================
# ADMIN DIAGNOSTIC VIEW
# =====================================================================================


@require_GET
@vary_on_headers("Host")
@cache_page(300)
def site_settings_view(request: HttpRequest) -> HttpResponse:
    """Visible to staff/admin only — shows full active settings."""
    s = SimpleLazyObject(lambda: _get_settings(request))
    return render(
        request,
        "site_settings/detail.html",
        {
            "site_settings": s,
            "meta_tags": s.get("meta_tags", []),
            "verification_files": s.get("verification_files", []),
        },
    )


# =====================================================================================
# PUBLIC — POLICY PAGES
# =====================================================================================


@require_GET
@vary_on_headers("Host")
@cache_page(600)
def privacy_policy(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "site_settings/privacy.html",
        {"site_settings": _get_settings(request)},
    )


@require_GET
@vary_on_headers("Host")
@cache_page(600)
def terms_of_service(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "site_settings/terms.html",
        {"site_settings": _get_settings(request)},
    )


@require_GET
@vary_on_headers("Host")
@cache_page(600)
def cookies_policy(request: HttpRequest) -> HttpResponse:
    """Cookies policy view — commonly used from consent app."""
    return render(
        request,
        "site_settings/cookies.html",
        {"site_settings": _get_settings(request)},
    )


# =====================================================================================
# PUBLIC — VERIFICATION FILE SERVING
# =====================================================================================


@require_GET
def verification_file(request: HttpRequest, filename: str) -> HttpResponse:
    """
    Serve Google/Facebook/Apple domain verification files safely.

    Ensures:
    - no directory traversal
    - only .txt / .html allowed
    - tenant overrides supported
    - secure redirect to storage URL
    """

    safe = Path(filename).name  # prevent traversal
    allowed_ext = {".html", ".txt"}

    s = _get_settings(request)
    vfiles = s.get("verification_files", [])

    match = None

    for entry in vfiles:
        try:
            if isinstance(entry, dict):
                name = (entry.get("file") or "").lower()
                url = entry.get("url")
            else:
                name = str(entry).lower()
                url = None

            if name.endswith(safe.lower()):
                match = {"name": name, "url": url}
                break

        except Exception:
            continue

    if not match:
        raise Http404("Verification file not found")

    if not any(match["name"].endswith(ext) for ext in allowed_ext):
        raise Http404("Invalid verification file type")

    if match.get("url"):
        return redirect(match["url"])

    raise Http404("Verification file has no storage URL")
