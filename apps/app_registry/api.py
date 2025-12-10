
from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.app_registry.services.registry_service import AppRegistryService

# Initialize service
_service = AppRegistryService()

# Legacy compatibility functions
def all_entries():
    """Legacy function - use AppRegistryService instead."""
    from apps.app_registry.models import AppRegistry
    return list(AppRegistry.objects.all())

def get_entry(app_id: str):
    """Legacy function - use AppRegistryService instead."""
    from apps.app_registry.models import AppRegistry
    return AppRegistry.objects.filter(app_id=app_id).first()

def register_or_update_entry(**kwargs):
    """Legacy function - use AppRegistryService instead."""
    from apps.app_registry.models import AppRegistry
    app_id = kwargs.get("app_id")
    if not app_id:
        raise ValueError("app_id is required")
    entry, created = AppRegistry.objects.update_or_create(
        app_id=app_id,
        defaults=kwargs
    )
    return entry


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


