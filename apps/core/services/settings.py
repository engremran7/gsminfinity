"""
Settings Service Implementation
Provides access to site settings without direct model imports in core.
"""
from typing import Any, Dict, Optional
from django.core.cache import cache
from apps.core.interfaces import SettingsProvider

# Sentinel object for cache checks
_CACHE_SENTINEL = object()


class DjangoSettingsProvider(SettingsProvider):
    """Implementation that uses Django's settings module"""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting from Django settings or site_settings model"""
        from django.conf import settings
        
        # First try Django settings
        if hasattr(settings, key):
            return getattr(settings, key)
        
        # Fall back to database settings (lazy import to avoid circular dependency)
        cache_key = f'site_setting_{key}'
        cached = cache.get(cache_key, _CACHE_SENTINEL)
        if cached is not _CACHE_SENTINEL:
            return cached
        
        try:
            from apps.site_settings.models import SiteSettings
            site_settings = SiteSettings.get_solo()
            value = getattr(site_settings, key.lower(), default)
            cache.set(cache_key, value, 300)  # Cache for 5 minutes
            return value
        except Exception:
            return default
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings as dictionary"""
        try:
            from apps.site_settings.models import SiteSettings
            site_settings = SiteSettings.get_solo()
            return {
                field.name: getattr(site_settings, field.name)
                for field in site_settings._meta.fields
            }
        except Exception:
            return {}


# Global instance
settings_provider = DjangoSettingsProvider()
