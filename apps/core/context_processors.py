"""
apps.core.context_processors
----------------------------
Enterprise-grade context processors.

Goals:
 - Lazy imports for startup/migration safety
 - Fully defensive (never break template rendering)
 - Zero branding (generic defaults)
 - Works seamlessly with new site_settings context processor (from apps.site_settings)
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

    s = None
    # 1. Safe, lazy lookup for the model instance
    try:
        # Check for model existence defensively
        from apps.site_settings.models import SiteSettings

        if hasattr(SiteSettings, "get_solo"):
            s = SiteSettings.get_solo()
        else:
            s = SiteSettings.objects.first()
    except Exception as exc:
        # This occurs if the app/model is not installed or migrations haven't run
        logger.debug("SiteSettings lookup skipped/failed: %s", exc)
        pass # s remains None

    # 2. Extract values or use defensive defaults
    return {
        "site_theme": {
            "primary_color": getattr(s, "primary_color", "#0d6efd"),
            "secondary_color": getattr(s, "secondary_color", "#6c757d"),
        },
        "site_settings_light": {
            "site_name": getattr(s, "site_name", "Site"),  # no branding
            "enable_signup": bool(getattr(s, "enable_signup", True)),
            # Use getattr with a safe fallback to prevent exceptions
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
                    SocialApp.objects.filter(sites=current_site).values_list(
                        "provider", flat=True
                    )
                )
            else:
                # Fallback query for single-site setups if get_current fails defensively
                enabled_providers = list(
                    SocialApp.objects.values_list("provider", flat=True)
                )
        except Exception as exc:
            logger.debug("SocialApp query failed: %s", exc)
            enabled_providers = []

    except Exception:
        # If allauth or sites not installed → gracefully degrade
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
        # Ensure we only show providers that are configured AND are in the preferred list
        available = (
            [p for p in preferred_list if p in enabled_providers]
            if enabled_providers
            else preferred_list
        )
        
        # FINAL SANITY CHECK: If the resulting list is empty, fall back to all enabled providers
        if not available and enabled_providers:
            available = enabled_providers
            
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
            # Assumes the custom User model has a 'preferred_region' field
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
        geoip_paths_configured = (
            getattr(settings, "GEOIP_PATH", None) or
            getattr(settings, "GEOIP_COUNTRY", None) or
            getattr(settings, "GEOIP_CITY", None)
        )
        if not geoip_paths_configured:
            return None

        try:
            from django.contrib.gis.geoip2 import GeoIP2  # type: ignore
        except Exception as exc:
            logger.debug("GeoIP2 unavailable (dependency missing): %s", exc)
            return None

        ip = _get_client_ip(request)
        if not ip or ip in ("127.0.0.1", "::1"): # Handle both IPv4 and IPv6 localhost
            return None

        try:
            g = GeoIP2()
            country = g.country_code(ip)
        except Exception as exc:
            logger.debug("GeoIP failure for %s: %s", ip, exc)
            return None

        if not country:
            return None

        region_map = getattr(settings, "COUNTRY_TO_REGION_MAP", None) or {}
        # Return region from map, or None if no region map entry exists
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

        # Extract only the language part (e.g., 'en' from 'en-US,en;q=0.9')
        primary_lang = header.split(",")[0].split(";")[0].split("-")[0].lower()
        if not primary_lang:
            return None

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

        # Return specific region or fall back to "global" if language is unrecognized
        return mapping.get(primary_lang, "global")

    except Exception as exc:
        logger.debug("_detect_region_via_language failed: %s", exc)
        return None


# =====================================================================
# IP EXTRACTION (HARDENED)
# =====================================================================
def _get_client_ip(request: HttpRequest) -> str:
    """
    Hardened IP extraction logic, respecting proxy headers and settings.
    """
    try:
        # NOTE: SECURE_PROXY_SSL_HEADER is often used to determine if the request is secure
        # but the common practice for getting the client IP is via X-Forwarded-For or X-Real-IP.
        
        # 1. Check standard proxy header X-Forwarded-For (most common for load balancers)
        # Trust only the *first* IP in the list (the actual client).
        fwd = request.META.get("HTTP_X_FORWARDED_FOR")
        if fwd:
            return fwd.split(",")[0].strip()
        
        # 2. Check for Real IP header (e.g., Nginx, Cloudflare)
        real_ip = request.META.get("HTTP_X_REAL_IP")
        if real_ip:
            return real_ip.strip()

        # 3. Fallback to Django's native address
        return request.META.get("REMOTE_ADDR", "127.0.0.1") or "127.0.0.1"
    
    except Exception:
        # Never fail on IP extraction
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
        # Use SITE_ID from settings, fallback to 1
        "SITE_ID": getattr(settings, "SITE_ID", 1), 
        "TIME_ZONE": getattr(settings, "TIME_ZONE", "UTC"),
    }