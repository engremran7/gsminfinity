
from __future__ import annotations

"""
Public API surface for the SEO app.
Resolved dynamically via AppService to avoid hard imports.
"""

from typing import Any, Dict

from apps.seo.models import SEOSettings


def get_settings() -> Dict[str, Any]:
    try:
        s = SEOSettings.get_solo()
        return {
            "seo_enabled": bool(getattr(s, "seo_enabled", True)),
            "auto_meta_enabled": bool(getattr(s, "auto_meta_enabled", False)),
            "auto_schema_enabled": bool(getattr(s, "auto_schema_enabled", False)),
            "auto_linking_enabled": bool(getattr(s, "auto_linking_enabled", False)),
        }
    except Exception:
        return {
            "seo_enabled": True,
            "auto_meta_enabled": False,
            "auto_schema_enabled": False,
            "auto_linking_enabled": False,
        }


__all__ = ["get_settings"]


