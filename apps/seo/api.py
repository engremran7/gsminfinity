from __future__ import annotations

"""
Public API surface for the SEO app.
Resolved dynamically via AppService to avoid hard imports.
"""

from typing import Any

from apps.seo.models import Redirect, SEOSettings


def get_settings() -> dict[str, Any]:
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


def get_redirects() -> list[dict]:
    qs = Redirect.objects.all().only("source", "target", "is_active")
    return [
        {"from_url": r.source, "to_url": r.target, "is_active": r.is_active} for r in qs
    ]


__all__ = ["get_settings", "get_redirects"]
