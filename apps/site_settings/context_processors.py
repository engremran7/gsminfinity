# apps/site_settings/context_processors.py
"""
Multi-tenant Site Settings Context Processor
--------------------------------------------
Provides tenant-aware configuration for all templates.

✅ Features:
- Per-site caching (unified key: active_site_settings_<site_domain>)
- Tenant-aware resolution via django.contrib.sites
- Safe fallback to global SiteSettings singleton
- TTL from model or 5 min default
- Consistent template context keys:
    site_settings, settings, meta_tags, verification_files
- Resilient to cache poisoning or missing relationships
"""

import logging
from django.core.cache import cache
from django.contrib.sites.shortcuts import get_current_site
from apps.site_settings.models import SiteSettings, TenantSiteSettings

log = logging.getLogger(__name__)


def site_settings(request):
    """
    Provide per-site settings and metadata to all templates.

    Returns:
        dict: {
            "site_settings": <TenantSiteSettings or SiteSettings>,
            "settings": <alias for site_settings>,
            "meta_tags": <QuerySet>,
            "verification_files": <QuerySet>,
        }
    """

    # ---------------------------------------------------------------
    # Determine current site and build unified cache key
    # ---------------------------------------------------------------
    try:
        current_site = get_current_site(request)
        site_identifier = getattr(current_site, "domain", None) or getattr(current_site, "id", "global")
    except Exception as exc:
        log.warning("Site resolution failed → %s", exc)
        current_site = None
        site_identifier = "global"

    cache_key = f"active_site_settings_{site_identifier}"
    settings_obj = cache.get(cache_key)

    # ---------------------------------------------------------------
    # Cache miss → resolve from DB
    # ---------------------------------------------------------------
    if not settings_obj:
        try:
            if current_site:
                # Prefer tenant-specific configuration
                settings_obj = (
                    TenantSiteSettings.objects.select_related("site")
                    .get(site=current_site)
                )
                log.debug("Loaded TenantSiteSettings for site: %s", current_site)
            else:
                raise TenantSiteSettings.DoesNotExist

        except TenantSiteSettings.DoesNotExist:
            log.debug("TenantSiteSettings missing; using global fallback.")
            settings_obj = SiteSettings.get_solo()

        except Exception as exc:
            log.exception("Failed to load site settings → %s", exc)
            settings_obj = SiteSettings.get_solo()

        # Cache resolved settings with TTL
        ttl = getattr(settings_obj, "cache_ttl_seconds", 300) or 300
        cache.set(cache_key, settings_obj, timeout=ttl)

    # ---------------------------------------------------------------
    # Related metadata normalization
    # ---------------------------------------------------------------
    try:
        meta_tags_qs = getattr(settings_obj, "meta_tags", None)
        meta_tags = meta_tags_qs.all() if hasattr(meta_tags_qs, "all") else SiteSettings.get_solo().meta_tags.all()
    except Exception as exc:
        log.warning("Meta tags fetch failed → %s", exc)
        meta_tags = SiteSettings.get_solo().meta_tags.none()

    try:
        verification_files_qs = getattr(settings_obj, "verification_files", None)
        verification_files = (
            verification_files_qs.all()
            if hasattr(verification_files_qs, "all")
            else SiteSettings.get_solo().verification_files.all()
        )
    except Exception as exc:
        log.warning("Verification files fetch failed → %s", exc)
        verification_files = SiteSettings.get_solo().verification_files.none()

    # ---------------------------------------------------------------
    # Return safe context for template rendering
    # ---------------------------------------------------------------
    return {
        "site_settings": settings_obj,
        "settings": settings_obj,  # legacy alias for backwards compatibility
        "meta_tags": meta_tags,
        "verification_files": verification_files,
    }
