from __future__ import annotations

from typing import Any

from apps.app_registry.models import AppEntry


def register_or_update_entry(
    *,
    app_id: str,
    display_name: str | None = None,
    routes: list[str] | None = None,
    namespaces: list[str] | None = None,
    locales: list[str] | None = None,
    required_consent: list[str] | None = None,
    min_identity_level: str = "none",
    feature_flags: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
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


def get_entry(app_id: str) -> AppEntry | None:
    try:
        return AppEntry.objects.get(app_id=app_id)
    except AppEntry.DoesNotExist:
        return None


def all_entries() -> list[AppEntry]:
    return list(AppEntry.objects.all())


__all__ = ["register_or_update_entry", "get_entry", "all_entries"]
