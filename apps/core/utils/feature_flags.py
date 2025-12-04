
from __future__ import annotations

import functools
from typing import Optional

from apps.core.app_service import AppService
from apps.site_settings.models import SiteSettings


@functools.lru_cache(maxsize=1)
def get_settings() -> Optional[SiteSettings]:
    """
    Small, process-local cache to avoid hitting the DB on every flag check.
    """
    try:
        return SiteSettings.get_solo()
    except Exception:
        return None


def seo_enabled() -> bool:
    try:
        seo_api = AppService.get("seo")
        if not seo_api:
            return False
        if hasattr(seo_api, "get_settings"):
            return bool(seo_api.get_settings().get("seo_enabled", False))
    except Exception:
        pass
    ss = get_settings()
    return bool(getattr(ss, "seo_enabled", False)) if ss else False


def ads_enabled() -> bool:
    try:
        ads_api = AppService.get("ads")
        if ads_api and hasattr(ads_api, "get_settings"):
            return bool(ads_api.get_settings().get("ads_enabled", False))
    except Exception:
        pass
    return False


def affiliate_enabled() -> bool:
    try:
        ads_api = AppService.get("ads")
        if ads_api and hasattr(ads_api, "get_settings"):
            return bool(ads_api.get_settings().get("affiliate_enabled", False))
    except Exception:
        pass
    return False


def auto_meta_enabled() -> bool:
    try:
        seo_api = AppService.get("seo")
        if not seo_api:
            return False
        if hasattr(seo_api, "get_settings"):
            return bool(seo_api.get_settings().get("auto_meta_enabled", False))
    except Exception:
        pass
    ss = get_settings()
    return bool(getattr(ss, "auto_meta_enabled", False)) if ss else False


def auto_schema_enabled() -> bool:
    try:
        seo_api = AppService.get("seo")
        if not seo_api:
            return False
        if hasattr(seo_api, "get_settings"):
            return bool(seo_api.get_settings().get("auto_schema_enabled", False))
    except Exception:
        pass
    ss = get_settings()
    return bool(getattr(ss, "auto_schema_enabled", False)) if ss else False


def auto_linking_enabled() -> bool:
    try:
        seo_api = AppService.get("seo")
        if not seo_api:
            return False
        if hasattr(seo_api, "get_settings"):
            return bool(seo_api.get_settings().get("auto_linking_enabled", False))
    except Exception:
        pass
    ss = get_settings()
    return bool(getattr(ss, "auto_linking_enabled", False)) if ss else False


def ad_aggressiveness() -> str:
    try:
        ads_api = AppService.get("ads")
        if not ads_api:
            return "balanced"
        if hasattr(ads_api, "get_settings"):
            return ads_api.get_settings().get("ad_aggressiveness_level", "balanced")
    except Exception:
        pass
    ss = get_settings()
    return getattr(ss, "ad_aggressiveness_level", "balanced") if ss else "balanced"


def reset_cache() -> None:
    """Used by signals/admin to clear process-local cache after updates."""
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        return


