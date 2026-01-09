"""
apps.consent.middleware

Enterprise-grade cookie-consent middleware.

- Callable middleware (WSGI + ASGI safe)
- Uses canonical utils (serializable policy payloads only)
- Session guarantee for anonymous visitors (best-effort)
- Robust ConsentRecord loading for user or session
- Exposes request.consent_* attributes for templates/analytics
- Defensive: never raises even if DB or cache is down
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.consent.models import ConsentRecord
from apps.consent.utils import (
    consent_cache_key,
    consent_cookie_settings,
    get_active_policy,
    resolve_site_domain,
    serialize_policy,
)

logger = logging.getLogger(__name__)


# =====================================================================
#  MAIN MIDDLEWARE
# =====================================================================
class ConsentMiddleware:
    """
    Middleware that attaches consent information to each request.

    Add:
        "apps.consent.middleware.ConsentMiddleware"
    AFTER:
        AuthenticationMiddleware
        SessionMiddleware
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Avoid unsafe, brand-specific defaults - now generic
        self.cookie_name, cookie_opts = consent_cookie_settings()
        self.cookie_max_age = int(cookie_opts.get("max_age", 60 * 60 * 24 * 365))
        self.cookie_samesite = cookie_opts.get("samesite", "Lax")
        self.cookie_secure = bool(cookie_opts.get("secure", not settings.DEBUG))
        self.cookie_domain = cookie_opts.get("domain") or None

    # =================================================================
    #  WSGI + ASGI entrypoint
    # =================================================================
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Baseline request attributes — MUST be set before any early returns
        request.has_cookie_consent = False
        request.consent_policy = None
        request.consent_version = None
        request.consent_categories = {}
        request.cookie_consent = SimpleNamespace()
        request.consent_summary = {}

        # -------------------------------
        # Ensure session exists (safe)
        # -------------------------------
        try:
            self._ensure_session(request)
        except Exception as exc:
            logger.debug("ConsentMiddleware: session bootstrap failed -> %s", exc)

        # -------------------------------
        # Determine domain
        # -------------------------------
        try:
            site_domain = resolve_site_domain(request)
        except Exception as exc:
            logger.debug("ConsentMiddleware: resolve_site_domain failed -> %s", exc)
            site_domain = None

        if not site_domain:
            site_domain = getattr(settings, "DEFAULT_SITE_DOMAIN", "default")

        # -------------------------------
        # Validate that cache_key works
        # -------------------------------
        try:
            consent_cache_key(site_domain)
        except Exception:
            logger.debug("ConsentMiddleware: cache key generation failure (ignored)")

        # -------------------------------
        # Load policy payload
        # -------------------------------
        try:
            policy_obj = get_active_policy(site_domain)
            policy_payload = serialize_policy(policy_obj)
        except Exception as exc:
            logger.debug("ConsentMiddleware: policy load failed -> %s", exc)
            policy_obj = None
            policy_payload = None

        if policy_payload:
            request.consent_policy = policy_payload
            request.consent_version = policy_payload.get("version")

        # -------------------------------
        # Try retrieving stored record
        # -------------------------------
        consent_record = None
        if request.consent_version:
            try:
                consent_record = self._get_consent_record(
                    request, request.consent_version, site_domain
                )
            except Exception as exc:
                logger.debug("ConsentMiddleware: record lookup failed -> %s", exc)

        # -------------------------------
        # Build baseline categories
        # -------------------------------
        try:
            categories, required = self._build_baseline_categories(policy_payload)
        except Exception:
            logger.exception(
                "ConsentMiddleware: baseline categories build failed, using safe fallback"
            )
            categories, required = {"functional": True}, {"functional"}

        # -------------------------------
        # Apply stored consent OR defaults
        # -------------------------------
        try:
            if consent_record:
                categories, has_opt_in = self._apply_consent_record(
                    categories, required, consent_record
                )
                # Treat presence of a record as consent recorded (even if only required categories)
                request.has_cookie_consent = True
            else:
                # Anonymous fallback (required=True, optional=False)
                for slug in list(categories.keys()):
                    categories[slug] = bool(slug in required)
                request.has_cookie_consent = False
        except Exception:
            logger.exception("ConsentMiddleware: applying record failed; fallback")
            for slug in list(categories.keys()):
                categories[slug] = bool(slug in required)
            request.has_cookie_consent = False

        # -------------------------------
        # Hard enforce required categories
        # -------------------------------
        for slug in required:
            categories[slug] = True

        # -------------------------------
        # Attach attributes
        # -------------------------------
        request.consent_categories = categories
        try:
            request.cookie_consent = SimpleNamespace(**categories)
        except Exception:
            request.cookie_consent = SimpleNamespace()

        request.consent_summary = {
            "version": request.consent_version,
            "active": bool(policy_payload),
            "has_consent": request.has_cookie_consent,
            "required": sorted(required),
            "site": site_domain,
        }

        logger.debug("ConsentMiddleware summary: %s", request.consent_summary)

        # =================================================================
        #  Downstream request
        # =================================================================
        response = self.get_response(request)

        # =================================================================
        #  Response hook (cookie writer)
        # =================================================================
        try:
            response = self.process_response(request, response, policy_payload)
        except Exception:
            logger.exception("ConsentMiddleware: response hook failed")

        return response

    # =====================================================================
    #  INTERNAL HELPERS
    # =====================================================================
    def _ensure_session(self, request: HttpRequest) -> None:
        """Ensure session exists for anonymous users."""
        session = getattr(request, "session", None)
        if not session:
            logger.warning("ConsentMiddleware: SessionMiddleware missing.")
            return

        try:
            if not session.session_key:
                session.create()
                session.modified = True
                logger.debug("ConsentMiddleware: new session created")
        except Exception as exc:
            logger.debug("ConsentMiddleware: session create failed -> %s", exc)

    # ---------------------------------------------------------------------
    def _get_consent_record(
        self, request: HttpRequest, policy_version: str, site_domain: str
    ) -> ConsentRecord | None:
        """
        Retrieve ConsentRecord applying database-accurate filters.
        """
        user = getattr(request, "user", None)

        # Get the policy object matching the version
        from apps.consent.models import ConsentPolicy

        policy = ConsentPolicy.objects.filter(
            version=policy_version, is_active=True
        ).first()
        if not policy:
            return None

        lookup = {"policy": policy}

        try:
            if user and getattr(user, "is_authenticated", False):
                lookup["user"] = user
            else:
                lookup["user__isnull"] = True
                # Use session_id instead of session_key
                lookup["session_id"] = (
                    getattr(request.session, "session_key", None) or ""
                )

            return (
                ConsentRecord.objects.filter(**lookup).order_by("-created_at").first()
            )
        except Exception as exc:
            logger.debug("ConsentMiddleware: ORM lookup failed -> %s", exc)
            return None

    # ---------------------------------------------------------------------
    def _build_baseline_categories(
        self, policy_payload: dict | None
    ) -> tuple[dict[str, bool], set[str]]:
        """Build baseline categories purely from the JSON snapshot."""
        categories: dict[str, bool] = {}
        required: set[str] = set()

        try:
            snap = (
                policy_payload.get("categories_snapshot", {}) if policy_payload else {}
            )
            if isinstance(snap, dict):
                for slug, data in snap.items():
                    slug = str(slug)
                    categories[slug] = False
                    if isinstance(data, dict) and data.get("required"):
                        required.add(slug)
        except Exception as exc:
            logger.debug("ConsentMiddleware: category parsing failed -> %s", exc)

        # Functional is always required
        categories.setdefault("functional", True)
        required.add("functional")

        return categories, required

    # ---------------------------------------------------------------------
    def _apply_consent_record(
        self, categories: dict[str, bool], required: set[str], record: ConsentRecord
    ) -> tuple[dict[str, bool], bool]:
        try:
            accepted = record.accepted_categories or {}
        except Exception:
            accepted = {}

        if accepted.get("reject_all"):
            for slug in list(categories.keys()):
                categories[slug] = slug in required
            return categories, False

        any_optional = False
        for slug in list(categories.keys()):
            if slug in required:
                categories[slug] = True
            else:
                categories[slug] = bool(accepted.get(slug))
                if categories[slug]:
                    any_optional = True

        return categories, any_optional

    # =====================================================================
    #  RESPONSE HOOK — cookie writer
    # =====================================================================
    def process_response(
        self, request: HttpRequest, response: HttpResponse, policy_payload: dict | None
    ) -> HttpResponse:
        """
        Write cookie storing accepted categories - best effort.
        NOTE: The view (accept_all/reject_all) already sets the cookie when user makes a choice.
        This middleware should NOT overwrite it. Only set if cookie doesn't exist yet.
        """
        if not policy_payload:
            return response

        # Check if cookie already exists (set by view or previous request)
        existing_cookie = request.COOKIES.get(self.cookie_name)
        if existing_cookie:
            # Cookie already set, don't overwrite
            return response

        # Only set cookie if user has given consent (has a record in DB)
        if not getattr(request, "has_cookie_consent", False):
            return response

        try:
            payload = dict(request.consent_categories or {"functional": True})
            value = json.dumps(payload, separators=(",", ":"))
            response.set_cookie(
                self.cookie_name,
                value,
                max_age=self.cookie_max_age,
                samesite=self.cookie_samesite,
                secure=self.cookie_secure,
                httponly=False,  # UI needs access
                domain=self.cookie_domain,
                path="/",
            )
        except Exception as exc:
            logger.debug("ConsentMiddleware: process_response error -> %s", exc)

        return response
