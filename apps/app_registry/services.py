
from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.app_registry.models import AppEntry


def register_or_update_entry(
    *,
    app_id: str,
    display_name: str | None = None,
    routes: List[str] | None = None,
    namespaces: List[str] | None = None,
    locales: List[str] | None = None,
    required_consent: List[str] | None = None,
    min_identity_level: str = "none",
    feature_flags: Dict[str, Any] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> AppEntry:
    entry, _ = AppEntry.objects.update_or_create(
        app_id=app_id,
        defaults={
            "display_name": display_name or app_id,
            "routes": routes or [],
            "i18n_namespaces": namespaces or [],
            "supported_locales": locales or [],
            "required_consent": required_consent or [],
            "min_identity_level": min_identity_level,
            "feature_flags": feature_flags or {},
            "metadata": metadata or {},
        },
    )
    return entry


def get_entry(app_id: str) -> Optional[AppEntry]:
    try:
        return AppEntry.objects.get(app_id=app_id)
    except AppEntry.DoesNotExist:
        return None


def all_entries() -> List[AppEntry]:
    return list(AppEntry.objects.all())


__all__ = ["register_or_update_entry", "get_entry", "all_entries"]


