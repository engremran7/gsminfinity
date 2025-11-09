# apps/core/cache.py
"""
Centralized cache utilities for GSMInfinity.

Provides:
- Named invalidation helpers for site settings and consent policy
- A simple get-with-fallback helper to avoid repeating cache-get/set logic
"""

from django.core.cache import cache
from django.contrib.sites.models import Site

class CacheManager:
    @staticmethod
    def invalidate_site_settings(site_id: int | None = None) -> None:
        """
        Invalidate site settings caches.
        If site_id provided, delete that tenant key; always delete global active key.
        """
        cache.delete("active_site_settings")
        if site_id:
            cache.delete(f"site_settings_{site_id}")
        # Optionally clear per-site cached keys if present
        try:
            for s in Site.objects.all():
                cache.delete(f"site_settings_{s.id}")
        except Exception:
            # Don't fail cache invalidation on startup/migration environment
            pass

    @staticmethod
    def invalidate_consent_policy(site_identifier: str | None = None) -> None:
        """
        Invalidate cached active consent policy.
        Use site_identifier or 'global'.
        """
        key = f"active_consent_policy_{site_identifier or 'global'}"
        cache.delete(key)
        cache.delete("active_consent_policy")

    @staticmethod
    def get_with_fallback(key: str, fallback_func, timeout: int = 300):
        """
        Get cached value or compute via fallback_func and set cache.
        """
        val = cache.get(key)
        if val is not None:
            return val
        val = fallback_func()
        cache.set(key, val, timeout=timeout)
        return val
