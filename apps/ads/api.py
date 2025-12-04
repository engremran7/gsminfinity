
from __future__ import annotations

"""
Public API surface for the Ads app.
Resolved dynamically via AppService to avoid hard imports.
"""

from typing import Any, Dict

from apps.ads.models import AdsSettings


def get_settings() -> Dict[str, Any]:
    try:
        s = AdsSettings.get_solo()
        return {
            "ads_enabled": bool(getattr(s, "ads_enabled", False)),
            "affiliate_enabled": bool(getattr(s, "affiliate_enabled", False)),
            "ad_networks_enabled": bool(getattr(s, "ad_networks_enabled", False)),
            "ad_aggressiveness_level": getattr(s, "ad_aggressiveness_level", "balanced"),
        }
    except Exception:
        return {
            "ads_enabled": False,
            "affiliate_enabled": False,
            "ad_networks_enabled": False,
            "ad_aggressiveness_level": "balanced",
        }


__all__ = ["get_settings"]


