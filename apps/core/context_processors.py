"""
apps.core.context_processors
----------------------------
Enterprise-grade context processors.

Goals:
 - Lazy imports for startup/migration safety
 - Fully defensive (never break template rendering)
 - Zero branding (generic defaults)
 - Works seamlessly with new site_settings context processor
 - Hardened region detection + provider resolution
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger(__name__)


# =====================================================================
# SITE SETTINGS (LIGHT SNAPSHOT)
# =====================================================================
def site_settings_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Lightweight supplemental settings for templates.
    NOTE:
        Full site settings come from the main context processor:
        → apps.site_settings.context_processor.site_settings
    This function ONLY adds small frequently-used fields and never duplicates logic.
    """

    # Safe, lazy lookup — never fatal
    try:
        from apps.site_settings.models import SiteSettings  # type: ignore
        try:
            s = SiteSettings.get_solo() if hasattr(SiteSettings, "get_solo") else SiteSettings.objects.first()
        except Exception as exc:
            logger.debug("SiteSettings lookup failure: %s", exc)
            s = None
    except Exception:
        s = None

    return {
        "site_theme": {
            "primary_color": getattr(s, "primary_color", "#0d6efd"),
            "secondary_color": getattr(s, "secondary_color", "#6c757d"),
        },
        "site_settings_light": {
            "site_name": getattr(s, "site_name", "Site"),  # no branding
            "enable_signup": bool(getattr(s, "enable_signup", True)),
            "recaptcha_site_key": getattr(s, "recaptcha_public_key", "") or "",
            "show_consent_banner": bool(getattr(s, "enable_notifications", False)),
        },
    }


# =====================================================================
# SOCIAL PROVIDER SELECTION (LOCATION AWARE)
# =====================================================================
def location_based_providers(request: HttpRequest) -> Dict[str, Any]:
    """
    Returns providers suggested for the user's region, filtered by site's enabled providers.

    Output:
        {
            "location_based_providers": [...],
            "user_region": "...",
            "all_enabled_providers": [...],
        }
    """
    enabled_providers: List[str] = []

    # -----------------------------------------------------------------------------
    # Lazy import allauth only if installed
    # -----------------------------------------------------------------------------
    try:
        from allauth.socialaccount.models import SocialApp  # type: ignore
        from django.contrib.sites.models import Site  # type: ignore

        try:
            current_site = Site.objects.get_current()
        except Exception as exc:
            logger.debug("Site.get_current() failed: %s", exc)
            current_site = None

        try:
            if current_site:
                enabled_providers = list(
                    SocialApp.objects.filter(sites=current_site).values_list("provider", flat=True)
                )
            else:
                enabled_providers = list(SocialApp.objects.values_list("provider", flat=True))
        except Exception as exc:
            logger.debug("SocialApp query failed: %s", exc)
            enabled_providers = []

    except Exception:
        # If allauth not installed → gracefully degrade
        enabled_providers = []

    # -----------------------------------------------------------------------------
    # Region detection
    # -----------------------------------------------------------------------------
    try:
        user_region = detect_user_region(request)
    except Exception as exc:
        logger.debug("detect_user_region failed: %s", exc)
        user_region = "global"

    # -----------------------------------------------------------------------------
    # Region → provider mapping
    # -----------------------------------------------------------------------------
    region_map = getattr(settings, "LOCATION_BASED_PROVIDERS", {}) or {}
    preferred_list = region_map.get(user_region, []) or []

    if not preferred_list:
        preferred_list = getattr(settings, "DEFAULT_SOCIAL_PROVIDERS", ["google"])

    # filter down to those enabled on the site
    try:
        available = [p for p in preferred_list if p in enabled_providers] if enabled_providers else preferred_list
    except Exception:
        available = preferred_list

    return {
        "location_based_providers": available,
        "user_region": user_region,
        "all_enabled_providers": enabled_providers,
    }


# =====================================================================
# REGION DETECTION
# =====================================================================
def detect_user_region(request: HttpRequest) -> str:
    """
    Hierarchical region detection:
        1) user preference (if authenticated)
        2) GeoIP (if available)
        3) Accept-Language header
        4) fallback = "global"
    """

    try:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            pref = getattr(user, "preferred_region", None)
            if pref:
                return str(pref)
    except Exception:
        pass

    try:
        geo_region = _detect_region_via_geoip(request)
        if geo_region:
            return geo_region
    except Exception:
        pass

    try:
        lang_region = _detect_region_via_language(request)
        if lang_region:
            return lang_region
    except Exception:
        pass

    return "global"


# =====================================================================
# GEOIP REGION
# =====================================================================
def _detect_region_via_geoip(request: HttpRequest) -> Optional[str]:
    try:
        geoip_path = getattr(settings, "GEOIP_PATH", None)
        if not geoip_path:
            return None

        try:
            from django.contrib.gis.geoip2 import GeoIP2  # type: ignore
        except Exception as exc:
            logger.debug("GeoIP2 unavailable: %s", exc)
            return None

        ip = _get_client_ip(request)
        if not ip or ip == "127.0.0.1":
            return None

        try:
            g = GeoIP2()
            country = g.country_code(ip)
        except Exception as exc:
            logger.debug("GeoIP failure for %s: %s", ip, exc)
            return None

        region_map = getattr(settings, "COUNTRY_TO_REGION_MAP", None) or {}
        return region_map.get(country, None)

    except Exception as exc:
        logger.debug("_detect_region_via_geoip unexpected error: %s", exc)
        return None


# =====================================================================
# LANGUAGE REGION
# =====================================================================
def _detect_region_via_language(request: HttpRequest) -> Optional[str]:
    try:
        header = request.META.get("HTTP_ACCEPT_LANGUAGE", "") or ""
        if not header:
            return None

        primary = header.split(",")[0].split("-")[0].lower()

        mapping = getattr(settings, "LANGUAGE_TO_REGION_MAP", None) or {
            "en": "global",
            "ar": "middle_east",
            "zh": "china",
            "ja": "asia",
            "ko": "asia",
            "ru": "russia",
            "de": "europe",
            "fr": "europe",
            "es": "europe",
            "it": "europe",
        }

        return mapping.get(primary, "global")

    except Exception as exc:
        logger.debug("_detect_region_via_language failed: %s", exc)
        return None


# =====================================================================
# IP EXTRACTION
# =====================================================================
def _get_client_ip(request: HttpRequest) -> str:
    try:
        fwd = request.META.get("HTTP_X_FORWARDED_FOR")
        if fwd:
            return fwd.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR", "127.0.0.1") or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


# =====================================================================
# CORE CONTEXT
# =====================================================================
def core_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Small, safe global flags for templates.
    """
    return {
        "DEBUG": getattr(settings, "DEBUG", False),
        "ENV": getattr(settings, "ENV", "production"),
        "SITE_ID": getattr(settings, "SITE_ID", 1),
        "TIME_ZONE": getattr(settings, "TIME_ZONE", "UTC"),
    }
