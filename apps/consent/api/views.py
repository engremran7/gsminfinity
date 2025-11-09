# apps/consent/api.py
"""
Enterprise Consent API Endpoints
================================
Features:
- Secure retrieval and update of consent records.
- Multi-site & multi-policy support.
- CSRF-protected and login-enforced.
- Safe JSON/form parsing with payload limits.
- Atomic, version-consistent writes.
- Unified cache coherence with ConsentMiddleware.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache

from apps.consent.models import ConsentRecord, ConsentPolicy

log = logging.getLogger(__name__)

# ============================================================
#  GET CONSENT STATUS
# ============================================================

@require_GET
def get_consent_status(request):
    """
    Retrieve the active consent policy and its categories for the current site.
    Used by front-end consent banners or SPAs.
    """
    try:
        # -----------------------------------------------
        # Resolve site and cache key
        # -----------------------------------------------
        site_domain = getattr(get_current_site(request), "domain", None) or request.get_host()
        cache_key = f"active_consent_policy_{site_domain}"

        # Attempt cached policy first
        policy = cache.get(cache_key)
        if not policy:
            policy = (
                ConsentPolicy.objects.filter(is_active=True, site_domain=site_domain)
                .order_by("-created_at")
                .first()
            )
            if policy:
                ttl = getattr(policy, "cache_ttl_seconds", 300) or 300
                cache.set(cache_key, policy, timeout=ttl)

        if not policy:
            log.warning("get_consent_status: no active policy for %s", site_domain)
            return JsonResponse({"error": "no_active_policy"}, status=404)

        return JsonResponse(
            {
                "version": policy.version,
                "site_domain": site_domain,
                "categories": policy.categories_snapshot or {},
            },
            status=200,
        )

    except Exception as exc:
        log.exception("get_consent_status: failed to fetch policy → %s", exc)
        return JsonResponse({"error": "internal_error"}, status=500)


# ============================================================
#  UPDATE CONSENT
# ============================================================

@csrf_protect  # ✅ safer than csrf_exempt
@login_required
@require_POST
def update_consent(request):
    """
    Stores or updates the user's consent record for the active policy.
    Enforces required categories and per-site version consistency.
    """
    try:
        # -----------------------------------------------
        # Step 1. Parse request data safely
        # -----------------------------------------------
        if request.content_type and "application/json" in request.content_type:
            try:
                raw = request.body.decode("utf-8") or "{}"
                if len(raw) > 1024 * 1024:  # 1 MB limit
                    return JsonResponse({"error": "payload_too_large"}, status=413)
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError("Invalid JSON structure")
            except Exception as exc:
                log.warning("update_consent: invalid JSON → %s", exc)
                return JsonResponse({"error": "invalid_json"}, status=400)
        else:
            data = request.POST.dict()

        # -----------------------------------------------
        # Step 2. Resolve active policy per site
        # -----------------------------------------------
        site_domain = getattr(get_current_site(request), "domain", None) or request.get_host()
        cache_key = f"active_consent_policy_{site_domain}"

        policy = cache.get(cache_key)
        if not policy:
            policy = (
                ConsentPolicy.objects.filter(is_active=True, site_domain=site_domain)
                .order_by("-created_at")
                .first()
            )
            if policy:
                ttl = getattr(policy, "cache_ttl_seconds", 300) or 300
                cache.set(cache_key, policy, timeout=ttl)

        if not policy:
            log.error("update_consent: no active policy for site=%s", site_domain)
            return JsonResponse({"error": "no_active_policy"}, status=404)

        # -----------------------------------------------
        # Step 3. Sanitize and normalize category choices
        # -----------------------------------------------
        categories_snapshot = policy.categories_snapshot or {}
        valid_slugs = set(categories_snapshot.keys()) | {"functional"}

        sanitized = {}
        for slug, val in data.items():
            if slug in valid_slugs:
                sanitized[slug] = bool(val)

        # Always accept required categories (cannot be turned off)
        for slug, meta in categories_snapshot.items():
            if meta.get("required"):
                sanitized[slug] = True

        # -----------------------------------------------
        # Step 4. Atomic write
        # -----------------------------------------------
        with transaction.atomic():
            ConsentRecord.objects.update_or_create(
                user=request.user,
                policy_version=policy.version,
                site_domain=site_domain,
                defaults={"accepted_categories": sanitized},
            )

        log.info("Consent updated for user=%s (policy=%s, site=%s)", request.user, policy.version, site_domain)
        return JsonResponse({"ok": True, "version": policy.version, "site_domain": site_domain}, status=200)

    except Exception as exc:
        log.exception("update_consent: unexpected error → %s", exc)
        return JsonResponse({"error": "internal_error"}, status=500)
