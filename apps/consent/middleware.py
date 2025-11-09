"""
apps.consent.middleware
------------------------
Enterprise-grade cookie-consent middleware for GSMInfinity.

✅ Features:
- Ensures sessions for anonymous users.
- Per-site active ConsentPolicy resolution with caching.
- ConsentRecord lookup (user or session-based).
- Required categories always enforced.
- “Reject all” support for optional categories.
- request.cookie_consent.<slug> namespace for templates.
- request.consent_summary for diagnostic / analytics.
- Fully compatible with Django 5.x and allauth ≥ 0.65.
"""

import logging
from types import SimpleNamespace
from typing import Dict, Optional

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse

from apps.consent.models import ConsentRecord, ConsentPolicy

logger = logging.getLogger(__name__)


class ConsentMiddleware(MiddlewareMixin):
    """
    Attaches consent-related metadata to every request.

    ⚙️ Notes
    -------
    • Works with MiddlewareMixin for async/sync support.
    • Gracefully handles missing DB tables or sessions.
    • Ensures one cached ConsentPolicy per site_id/domain.
    """

    def process_request(self, request: HttpRequest) -> None:
        """Inject consent context into request safely."""

        # -----------------------------------------------------------
        # 1️⃣ Ensure session exists (for anonymous users)
        # -----------------------------------------------------------
        try:
            if not getattr(request, "session", None):
                logger.warning("ConsentMiddleware: SessionMiddleware missing.")
            elif not request.session.session_key:
                request.session.create()
                request.session.modified = True
                logger.debug("ConsentMiddleware: created new session for anonymous user.")
        except Exception as exc:
            logger.debug("ConsentMiddleware: session init failed → %s", exc)

        # -----------------------------------------------------------
        # 2️⃣ Resolve current site (with safe fallback)
        # -----------------------------------------------------------
        try:
            current_site = get_current_site(request)
            site_domain = getattr(current_site, "domain", None) or request.get_host()
            site_identifier = getattr(current_site, "id", site_domain)
        except Exception as exc:
            logger.warning("ConsentMiddleware: failed to resolve site → %s", exc)
            site_domain = getattr(request, "get_host", lambda: "default")() or "default"
            site_identifier = site_domain

        # -----------------------------------------------------------
        # 3️⃣ Initialize baseline request attributes
        # -----------------------------------------------------------
        request.has_cookie_consent = False
        request.consent_policy: Optional[ConsentPolicy] = None
        request.consent_version: Optional[str] = None
        request.consent_categories: Dict[str, bool] = {}
        request.cookie_consent = SimpleNamespace()
        request.consent_summary = {}

        # -----------------------------------------------------------
        # 4️⃣ Retrieve (or cache) active ConsentPolicy per site
        # -----------------------------------------------------------
        cache_key = f"active_consent_policy_{site_identifier}"
        policy: Optional[ConsentPolicy] = cache.get(cache_key)

        if policy is None:
            try:
                policy = (
                    ConsentPolicy.objects.filter(is_active=True, site_domain=site_domain)
                    .order_by("-created_at")
                    .first()
                )
                cache_ttl = getattr(settings, "CONSENT_POLICY_CACHE_TTL", 300)
                cache.set(cache_key, policy, timeout=cache_ttl)
                logger.debug("ConsentMiddleware: cache MISS for %s", site_domain)
            except Exception as exc:
                logger.debug("ConsentMiddleware: policy lookup error → %s", exc)
                policy = None
        else:
            logger.debug("ConsentMiddleware: cache HIT for %s", site_domain)

        if policy:
            request.consent_policy = policy
            request.consent_version = policy.version

        # -----------------------------------------------------------
        # 5️⃣ Load ConsentRecord (user or session-based)
        # -----------------------------------------------------------
        consent_record: Optional[ConsentRecord] = None
        if request.consent_version:
            lookup = {
                "policy_version": request.consent_version,
                "site_domain": site_domain,
            }
            user = getattr(request, "user", None)
            if user and getattr(user, "is_authenticated", False):
                lookup["user"] = user
            else:
                lookup["session_key"] = getattr(request.session, "session_key", None)

            try:
                consent_record = ConsentRecord.objects.filter(**lookup).first()
                logger.debug("ConsentMiddleware: record lookup %s", lookup)
            except Exception as exc:
                logger.debug("ConsentMiddleware: record query failed → %s", exc)

        # -----------------------------------------------------------
        # 6️⃣ Build categories baseline
        # -----------------------------------------------------------
        categories: Dict[str, bool] = {}
        required_slugs = set()
        if policy and policy.categories_snapshot:
            for slug, data in (policy.categories_snapshot or {}).items():
                categories[slug] = False
                if data.get("required"):
                    required_slugs.add(slug)
        categories.setdefault("functional", True)

        # -----------------------------------------------------------
        # 7️⃣ Apply consent record preferences
        # -----------------------------------------------------------
        if consent_record:
            accepted = consent_record.accepted_categories or {}

            if accepted.get("reject_all"):
                # Only required + functional remain true
                for slug in categories:
                    categories[slug] = slug in required_slugs or slug == "functional"
                request.has_cookie_consent = False
                logger.debug("ConsentMiddleware: reject_all enforced for %s", site_domain)
            else:
                for slug in categories:
                    if slug in required_slugs or slug == "functional":
                        categories[slug] = True
                    else:
                        categories[slug] = bool(accepted.get(slug))
                # ✅ has_cookie_consent → True only if optional category accepted
                optional_accepted = any(
                    slug not in required_slugs and slug != "functional" and val
                    for slug, val in categories.items()
                )
                request.has_cookie_consent = optional_accepted
                logger.debug("ConsentMiddleware: consent record applied for %s", site_domain)
        else:
            # Default required+functional only
            for slug in categories:
                categories[slug] = slug in required_slugs or slug == "functional"
            logger.debug("ConsentMiddleware: no record, applied defaults.")

        # -----------------------------------------------------------
        # 8️⃣ Ensure required categories enforced (safety net)
        # -----------------------------------------------------------
        for slug in required_slugs:
            categories[slug] = True

        # -----------------------------------------------------------
        # 9️⃣ Attach namespace + summary
        # -----------------------------------------------------------
        request.consent_categories = categories
        request.cookie_consent = SimpleNamespace(**categories)
        request.consent_summary = {
            "version": request.consent_version,
            "active": bool(policy),
            "has_consent": request.has_cookie_consent,
            "required": sorted(required_slugs),
            "site": site_domain,
        }

        logger.debug("ConsentMiddleware summary for %s: %s", site_domain, request.consent_summary)

    # -----------------------------------------------------------
    # Response hook (optional)
    # -----------------------------------------------------------
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Hook for cookie updates or metrics injection.

        ⚠️ Keep synchronous — do not return awaitables to maintain
        middleware chain integrity under Django async.
        """
        # Example future use:
        # if getattr(request, "has_cookie_consent", False):
        #     response.set_cookie("cookie_consent", "1", httponly=True)
        return response
