from __future__ import annotations

import functools
from typing import Optional

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
    ss = get_settings()
    return bool(getattr(ss, "seo_enabled", False)) if ss else False


def ads_enabled() -> bool:
    ss = get_settings()
    return bool(getattr(ss, "ads_enabled", False)) if ss else False


def affiliate_enabled() -> bool:
    ss = get_settings()
    return bool(getattr(ss, "affiliate_enabled", False)) if ss else False


def auto_meta_enabled() -> bool:
    ss = get_settings()
    return bool(getattr(ss, "auto_meta_enabled", False)) if ss else False


def auto_schema_enabled() -> bool:
    ss = get_settings()
    return bool(getattr(ss, "auto_schema_enabled", False)) if ss else False


def auto_linking_enabled() -> bool:
    ss = get_settings()
    return bool(getattr(ss, "auto_linking_enabled", False)) if ss else False


def ad_aggressiveness() -> str:
    ss = get_settings()
    return getattr(ss, "ad_aggressiveness_level", "balanced") if ss else "balanced"


def reset_cache() -> None:
    """Used by signals/admin to clear process-local cache after updates."""
    try:
        get_settings.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        return
