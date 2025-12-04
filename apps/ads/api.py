
from __future__ import annotations

"""
Public API surface for the Ads app.
Resolved dynamically via AppService to avoid hard imports.
"""

from typing import Any, Dict
import logging

from apps.ads.models import AdsSettings

logger = logging.getLogger(__name__)


def get_settings() -> Dict[str, Any]:
    """
    Return a safe snapshot of ads configuration for use via AppService.
    Fail closed with explicit logging if settings cannot be loaded.
    """
    try:
        s = AdsSettings.get_solo()
    except Exception as exc:
        logger.error(
            "AdsSettings.get_solo failed; falling back to safe defaults",
            exc_info=True,
            extra={"error": str(exc)},
        )
        return {
            "ads_enabled": False,
            "affiliate_enabled": False,
            "ad_networks_enabled": False,
            "ad_aggressiveness_level": "balanced",
        }

    return {
        "ads_enabled": bool(getattr(s, "ads_enabled", False)),
        "affiliate_enabled": bool(getattr(s, "affiliate_enabled", False)),
        "ad_networks_enabled": bool(getattr(s, "ad_networks_enabled", False)),
        "ad_aggressiveness_level": getattr(s, "ad_aggressiveness_level", "balanced"),
    }


__all__ = ["get_settings"]


