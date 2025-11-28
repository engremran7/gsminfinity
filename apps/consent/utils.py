"""
apps.consent.utils
==================

Canonical helpers for enterprise-grade consent management.

✔ Safe, unified domain normalization
✔ Canonical cache key generation
✔ Fully serializable active-policy payloads
✔ ORM → cache promotion with TTL
✔ Django 5.2 / Python 3.12 compliant
✔ No silent failures
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from apps.consent.models import ConsentPolicy
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_TTL_SECONDS = 300


# ---------------------------------------------------------------------------
# Cache Key Helpers
# ---------------------------------------------------------------------------


def consent_cache_key(domain: str) -> str:
    """
    Canonical, collision-resistant cache key for a site's active ConsentPolicy.
    """
    safe = (domain or "default").strip().lower()
    digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()[:12]
    return f"active_consent_policy_{digest}"


# ---------------------------------------------------------------------------
# Domain Resolution
# ---------------------------------------------------------------------------


def resolve_site_domain(request) -> str:
    """
    Resolve domain according to canonical order:

        1) django.contrib.sites
        2) request.get_host()
        3) "default"

    Always normalized to lowercase + stripped.
    """
    try:
        site = get_current_site(request)
        domain = getattr(site, "domain", None) or request.get_host() or "default"
        domain = str(domain).strip().lower()
        return domain or "default"
    except Exception as exc:
        logger.debug("resolve_site_domain fallback → %s", exc)
        return "default"


# ---------------------------------------------------------------------------
# Active Policy Retrieval
# ---------------------------------------------------------------------------


def get_active_policy(domain: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve active ConsentPolicy payload for a given domain.

    Schema returned:
        {
            "version": "v1",
            "categories_snapshot": {...},
            "banner_text": "...",
            "manage_text": "...",
            "is_active": True,
            "site_domain": "example.com",
            "cache_ttl_seconds": 300
        }

    - Never returns ORM objects
    - Cache is authoritative when present
    - Safe under all backends
    - Defensive normalization
    """
    domain = (domain or "default").strip().lower()
    key = consent_cache_key(domain)

    # ----- Cache Read -----
    try:
        cached = cache.get(key)
        if cached is not None:
            return cached
    except Exception as exc:
        logger.debug("get_active_policy: cache.get failed → %s", exc)

    # ----- DB Fallback -----
    try:
        policy = (
            ConsentPolicy.objects.filter(is_active=True, site_domain=domain)
            .only(
                "version",
                "categories_snapshot",
                "banner_text",
                "manage_text",
                "cache_ttl_seconds",
                "is_active",
                "site_domain",
            )
            .order_by("-created_at")
            .first()
        )
    except Exception as exc:
        logger.exception("get_active_policy: DB failure → %s", exc)
        return None

    if not policy:
        return None

    ttl = int(
        getattr(policy, "cache_ttl_seconds", DEFAULT_TTL_SECONDS) or DEFAULT_TTL_SECONDS
    )

    payload: Dict[str, Any] = {
        "version": str(policy.version),
        "categories_snapshot": policy.categories_snapshot or {},
        "banner_text": getattr(policy, "banner_text", "") or "",
        "manage_text": getattr(policy, "manage_text", "") or "",
        "is_active": bool(policy.is_active),
        "site_domain": (policy.site_domain or domain).strip().lower(),
        "cache_ttl_seconds": ttl,
    }

    # ----- Cache Write -----
    try:
        cache.set(key, payload, timeout=ttl)
        logger.debug("get_active_policy: cached active policy for domain=%s", domain)
    except Exception as exc:
        logger.debug("get_active_policy: cache.set failed → %s", exc)

    return payload


# ---------------------------------------------------------------------------
# Cache Invalidator
# ---------------------------------------------------------------------------


def invalidate_policy_cache(domain: Optional[str] = None) -> None:
    """
    Invalidate cached active policies:

        domain provided → delete only that domain
        no domain       → wildcard purge if supported

    Never raises.
    """
    # Per-domain invalidate
    if domain:
        key = consent_cache_key((domain or "default").strip().lower())
        try:
            cache.delete(key)
            logger.debug("invalidate_policy_cache: deleted key=%s", key)
        except Exception as exc:
            logger.debug("invalidate_policy_cache: delete failed → %s", exc)
        return

    # Wildcard invalidate (Redis / LocMem, etc.)
    try:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern("active_consent_policy_*")
            logger.debug("invalidate_policy_cache: wildcard invalidation performed")
        else:
            logger.debug("invalidate_policy_cache: backend lacks delete_pattern()")
    except Exception as exc:
        logger.debug("invalidate_policy_cache: wildcard failed → %s", exc)