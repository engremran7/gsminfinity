"""
Enterprise-grade Site Settings Context Processor (FINAL, SYNC-ONLY)

- 100% synchronous (no await / no sync_to_async / no async context switching)
- WSGI + ASGI safe
- ORM calls fully wrapped in defensive guards
- Never leaks exceptions into templates
- Returns consistent, normalized schema
- No recursion risk, no unsafe attributes
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable
from typing import Any

from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import HttpRequest
from django.templatetags.static import static

from apps.core.app_service import AppService

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 300
CACHE_KEY_PREFIX = "active_site_settings"


# ---------------------------------------------------------------------
# KEY HELPERS
# ---------------------------------------------------------------------
def _safe_domain_key(domain: str | None) -> str:
    """Convert domain to cache key (collision-resistant, no unsafe chars)."""
    safe = (domain or "global").strip().lower()
    digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()[:16]
    return f"{CACHE_KEY_PREFIX}_{digest}"


def _iter_related(obj: Any, attr: str) -> Iterable:
    """Returns a tuple for all related items safely & consistently."""
    try:
        rel = getattr(obj, attr, None)
        if rel is None:
            return ()
        if hasattr(rel, "all"):
            # Execute ORM query defensively
            return tuple(rel.all())
        if isinstance(rel, (list, tuple, set)):
            return tuple(rel)
        return (rel,)
    except Exception:
        # Never break template rendering due to ORM lookup failure
        return ()


def _file_url_or_default(file_field, default_static_path: str) -> str:
    """Safe URL resolver for file fields."""
    try:
        if file_field and getattr(file_field, "url", None):
            url = file_field.url
            if isinstance(url, str) and url.strip():
                return url
    except Exception:
        pass
    return static(default_static_path)


# ---------------------------------------------------------------------
# SERIALIZER (pure sync, full defensive)
# ---------------------------------------------------------------------
def _safe_defaults() -> dict[str, Any]:
    """Central default payload (no recursion)."""
    return {
        "id": None,
        "site_domain": "global",
        "site_name": "Site",
        "site_header": "Admin",
        "site_description": "",
        "logo": static("img/default-logo.svg"),
        "dark_logo": static("img/default-logo-dark.svg"),
        "favicon": static("img/default-favicon.svg"),
        "theme": "default",
        "primary_color": "#0d6efd",
        "secondary_color": "#6c757d",
        "enable_signup": True,
        "enable_notifications": True,
        "maintenance_mode": False,
        "force_https": False,
        "recaptcha_enabled": False,
        # Feature toggles (ads/seo)
        "seo_enabled": False,
        "auto_meta_enabled": False,
        "auto_schema_enabled": False,
        "auto_linking_enabled": False,
        "ads_enabled": False,
        "affiliate_enabled": False,
        "ad_networks_enabled": False,
        "ad_aggressiveness_level": "balanced",
        "enable_blog": False,
        "enable_blog_comments": False,
        "cache_ttl_seconds": DEFAULT_TTL_SECONDS,
        "meta_tags": [],
        "verification_files": [],
    }


def _serialize(obj: Any) -> dict[str, Any]:
    """Convert ORM object to dict (fully isolated, exception-proof)."""

    if obj is None:
        return _safe_defaults()

    try:
        # domain fallback logic
        site_domain = getattr(obj, "site_domain", None) or "global"

        # META TAGS
        meta_tags = []
        for m in _iter_related(obj, "meta_tags"):
            name = getattr(m, "name", None) or getattr(m, "name_attr", None)
            content = getattr(m, "content", None) or getattr(m, "content_attr", None)
            if isinstance(name, str) and name.strip():
                meta_tags.append(
                    {
                        "name": name.strip(),
                        "content": content or "",
                    }
                )

        # VERIFICATION FILES
        verification_files = []
        for f in _iter_related(obj, "verification_files"):
            file_field = getattr(f, "file", None)
            raw_name = (
                getattr(file_field, "name", None) or getattr(f, "filename", None) or ""
            )
            raw_url = getattr(file_field, "url", None) or ""

            filename = raw_name if isinstance(raw_name, str) else ""
            url = raw_url if isinstance(raw_url, str) else ""

            if not url.strip():
                url = static("img/default-verification.txt")

            verification_files.append(
                {
                    "filename": filename,
                    "url": url,
                    "provider": getattr(f, "provider", "") or "",
                }
            )

        ttl = getattr(obj, "cache_ttl_seconds", DEFAULT_TTL_SECONDS)
        try:
            ttl = int(ttl)
        except Exception:
            ttl = DEFAULT_TTL_SECONDS

        return {
            "id": getattr(obj, "id", None),
            "site_domain": site_domain,
            "site_name": getattr(obj, "site_name", "Site"),
            "site_header": getattr(obj, "site_header", "Admin"),
            "site_description": getattr(obj, "site_description", "") or "",
            "logo": _file_url_or_default(
                getattr(obj, "logo", None), "img/default-logo.svg"
            ),
            "dark_logo": _file_url_or_default(
                getattr(obj, "dark_logo", None), "img/default-logo-dark.svg"
            ),
            "favicon": _file_url_or_default(
                getattr(obj, "favicon", None), "img/default-favicon.svg"
            ),
            "theme": getattr(obj, "theme", "default"),
            "primary_color": getattr(obj, "primary_color", "#0d6efd"),
            "secondary_color": getattr(obj, "secondary_color", "#6c757d"),
            "enable_signup": bool(getattr(obj, "enable_signup", True)),
            "enable_notifications": bool(getattr(obj, "enable_notifications", True)),
            "maintenance_mode": bool(getattr(obj, "maintenance_mode", False)),
            "force_https": bool(getattr(obj, "force_https", False)),
            "recaptcha_enabled": bool(getattr(obj, "recaptcha_enabled", False)),
            # Feature toggles (admin controlled)
            "enable_blog": bool(getattr(obj, "enable_blog", False)),
            "enable_blog_comments": bool(getattr(obj, "enable_blog_comments", False)),
            # Ads/SEO toggles (for template gating)
            "seo_enabled": bool(getattr(obj, "seo_enabled", False)),
            "auto_meta_enabled": bool(getattr(obj, "auto_meta_enabled", False)),
            "auto_schema_enabled": bool(getattr(obj, "auto_schema_enabled", False)),
            "auto_linking_enabled": bool(getattr(obj, "auto_linking_enabled", False)),
            "ads_enabled": bool(getattr(obj, "ads_enabled", False)),
            "affiliate_enabled": bool(getattr(obj, "affiliate_enabled", False)),
            "ad_networks_enabled": bool(getattr(obj, "ad_networks_enabled", False)),
            "ad_aggressiveness_level": getattr(
                obj, "ad_aggressiveness_level", "balanced"
            )
            or "balanced",
            "cache_ttl_seconds": ttl,
            "meta_tags": meta_tags,
            "verification_files": verification_files,
        }

    except Exception:
        logger.error("_serialize failed → defaults used", exc_info=True)
        return _safe_defaults()


def _merge_app_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Overlay per-app settings resolved via AppService onto the payload.
    Keeps payload keys stable for templates while using decentralized settings.
    """
    merged = dict(payload)
    try:
        ads_api = AppService.get("ads")
        if ads_api and hasattr(ads_api, "get_settings"):
            ads = ads_api.get_settings()
            merged.update(
                {
                    "ads_enabled": ads.get("ads_enabled", False),
                    "affiliate_enabled": ads.get("affiliate_enabled", False),
                    "ad_networks_enabled": ads.get("ad_networks_enabled", False),
                    "ad_aggressiveness_level": ads.get(
                        "ad_aggressiveness_level",
                        merged.get("ad_aggressiveness_level", "balanced"),
                    ),
                }
            )
        elif ads_api is None:
            merged.update(
                {
                    "ads_enabled": False,
                    "affiliate_enabled": False,
                    "ad_networks_enabled": False,
                }
            )
    except Exception:
        pass

    try:
        seo_api = AppService.get("seo")
        if seo_api and hasattr(seo_api, "get_settings"):
            seo = seo_api.get_settings()
            merged.update(
                {
                    "seo_enabled": seo.get("seo_enabled", False),
                    "auto_meta_enabled": seo.get("auto_meta_enabled", False),
                    "auto_schema_enabled": seo.get("auto_schema_enabled", False),
                    "auto_linking_enabled": seo.get("auto_linking_enabled", False),
                }
            )
        elif seo_api is None:
            merged.update(
                {
                    "seo_enabled": False,
                    "auto_meta_enabled": False,
                    "auto_schema_enabled": False,
                    "auto_linking_enabled": False,
                }
            )
    except Exception:
        pass

    try:
        blog_api = AppService.get("blog")
        if blog_api and hasattr(blog_api, "get_settings"):
            blog = blog_api.get_settings()
            merged.update(
                {
                    "enable_blog": blog.get("enable_blog", False),
                    "enable_blog_comments": blog.get("enable_blog_comments", False),
                    "allow_user_blog_posts": blog.get("allow_user_blog_posts", False),
                }
            )
        elif blog_api is None:
            merged.update(
                {
                    "enable_blog": False,
                    "enable_blog_comments": False,
                    "allow_user_blog_posts": False,
                }
            )
    except Exception:
        pass

    try:
        comments_api = AppService.get("comments")
        if comments_api and hasattr(comments_api, "get_settings"):
            cset = comments_api.get_settings()
            merged.update({"enable_comments": cset.get("enable_comments", False)})
        elif comments_api is None:
            merged.update({"enable_comments": False})
    except Exception:
        pass

    return merged


# ---------------------------------------------------------------------
# ORM LOADER (100% synchronous)
# ---------------------------------------------------------------------
def _load_sync(site):
    """Loads global settings in strict sync mode."""
    try:
        # Lazy Import
        from apps.site_settings import models as m
    except Exception:
        logger.error("Import failure: apps.site_settings missing", exc_info=True)
        return None

    try:
        qs = m.SiteSettings.objects.prefetch_related("meta_tags", "verification_files")
        if hasattr(m.SiteSettings, "get_solo"):
            return m.SiteSettings.get_solo()
        return qs.first()
    except Exception:
        logger.debug("_load_sync failed -> None")
        return None


# ---------------------------------------------------------------------
# MAIN CONTEXT PROCESSOR (FULLY SYNC, FULLY SAFE)
# ---------------------------------------------------------------------
def site_settings(request: HttpRequest) -> dict[str, Any]:
    try:
        # 1. Determine Auth status (Request-specific, cannot be cached with site settings)
        is_authenticated = False
        try:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                is_authenticated = True
        except Exception:
            pass
        # --------------------------------------------------------------------

        try:
            site = get_current_site(request)
            domain = (
                getattr(site, "domain", None) or f"id-{getattr(site, 'id', 'global')}"
            )
        except Exception:
            site = None
            domain = "global"

        cache_key = _safe_domain_key(domain)

        # Cache hit
        try:
            cached = cache.get(cache_key)
            if isinstance(cached, dict):
                # Inject request-specific context (auth status)
                merged = _merge_app_settings(cached)
                return {
                    "site_settings": merged,
                    "settings": merged,
                    "meta_tags": merged.get("meta_tags", []),
                    "verification_files": merged.get("verification_files", []),
                    "auth_is_authenticated": is_authenticated,  # 🔥 FIXED: Non-cached variable injected
                }
        except Exception:
            pass

        # Load ORM → serialize
        raw_obj = _load_sync(site)
        payload = _merge_app_settings(_serialize(raw_obj))

        # Cache write
        try:
            cache.set(cache_key, payload, timeout=payload["cache_ttl_seconds"])
        except Exception:
            pass

        # Final Return
        # Inject request-specific context (auth status)
        return {
            "site_settings": payload,
            "settings": payload,
            "meta_tags": payload.get("meta_tags", []),
            "verification_files": payload.get("verification_files", []),
            "auth_is_authenticated": is_authenticated,  # 🔥 FIXED: Non-cached variable injected
        }

    except Exception:
        logger.error("site_settings processor fatal → defaults", exc_info=True)
        payload = _safe_defaults()
        # Ensure 'auth_is_authenticated' is returned even on fatal failure
        return {
            "site_settings": payload,
            "settings": payload,
            "meta_tags": [],
            "verification_files": [],
            "auth_is_authenticated": False,  # 🔥 FIXED: Non-cached variable injected
        }


# Alias (keeps backwards compatibility)
def global_settings(request: HttpRequest) -> dict[str, Any]:
    return site_settings(request)
