
from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.app_registry.services import all_entries, get_entry, register_or_update_entry


def list_registry() -> List[Dict[str, Any]]:
    return [
        {
            "app_id": e.app_id,
            "display_name": e.display_name,
            "routes": e.routes,
            "i18n_namespaces": e.i18n_namespaces,
            "supported_locales": e.supported_locales,
            "required_consent": e.required_consent,
            "min_identity_level": e.min_identity_level,
            "feature_flags": e.feature_flags,
            "metadata": e.metadata,
        }
        for e in all_entries()
    ]


def registry_entry(app_id: str) -> Optional[Dict[str, Any]]:
    e = get_entry(app_id)
    if not e:
        return None
    return {
        "app_id": e.app_id,
        "display_name": e.display_name,
        "routes": e.routes,
        "i18n_namespaces": e.i18n_namespaces,
        "supported_locales": e.supported_locales,
        "required_consent": e.required_consent,
        "min_identity_level": e.min_identity_level,
        "feature_flags": e.feature_flags,
        "metadata": e.metadata,
    }


__all__ = ["list_registry", "registry_entry", "register_or_update_entry"]


