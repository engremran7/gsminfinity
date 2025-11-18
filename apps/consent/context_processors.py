"""
apps.consent.context_processors
===============================

Injects consent state and metadata into all Django templates.

- Django 5.2+ / Python 3.12+
- Async-safe, thread-safe, side-effect free
- Compatible with canonical banner structure:
      {slug: {"checked": bool, "required": bool, "name": str}}
- Fully backward-compatible with older variables
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from django.http import HttpRequest
from django.utils.functional import SimpleLazyObject
from django.conf import settings

from apps.consent.models import ConsentPolicy

logger = logging.getLogger(__name__)


def consent_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Canonical consent context for templates.

    Provides:
      - has_cookie_consent: bool
      - cookie_consent_categories: dict[str, bool]
      - consent_categories: dict[str, {checked, required, name}]
      - consent_version, consent_summary
      - active_consent_policy: lazy-loaded ConsentPolicy | None
      - consent_cookie_* settings

    Never raises — always returns safe defaults.
    """

    def _lazy_active_policy():
        """Lazy resolver for active ConsentPolicy (middleware-first)."""
        try:
            existing = getattr(request, "consent_policy", None)
            if existing is not None:
                return existing
            return ConsentPolicy.get_active()
        except Exception as exc:
            logger.warning("Consent context lazy policy failed: %s", exc)
            return None

    try:
        raw = getattr(request, "consent_categories", {}) or {}

        cookie_map: Dict[str, bool] = {}
        canonical: Dict[str, Dict[str, Any]] = {}

        # -----------------------------
        # Build canonical structured map
        # -----------------------------
        try:
            for slug, val in dict(raw).items():
                if isinstance(val, dict):
                    checked = bool(val.get("checked", val.get("accepted", False)))
                    required = bool(val.get("required", False))
                    name = val.get("name", slug)
                else:
                    checked = bool(val)
                    required = False
                    name = slug

                cookie_map[str(slug)] = checked
                canonical[str(slug)] = {
                    "checked": checked,
                    "required": required,
                    "name": name,
                }
        except Exception:
            # if any corruption or unexpected structure occurs
            cookie_map = {"functional": True}
            canonical = {
                "functional": {"checked": True, "required": True, "name": "functional"}
            }

        # ------------------------------------------------------------------
        # Guarantee presence of functional cookies — required by EU regulation
        # ------------------------------------------------------------------
        if "functional" not in canonical:
            canonical["functional"] = {
                "checked": True,
                "required": True,
                "name": "functional",
            }
            cookie_map.setdefault("functional", True)
        else:
            canonical["functional"]["required"] = True
            cookie_map.setdefault("functional", True)

        # ---------------------------
        # Construct final safe context
        # ---------------------------
        ctx: Dict[str, Any] = {
            "has_cookie_consent": bool(getattr(request, "has_cookie_consent", False)),
            "cookie_consent_categories": cookie_map,
            "consent_categories": canonical,  # canonical, banner-safe
            "consent_version": getattr(request, "consent_version", None),
            "consent_summary": dict(getattr(request, "consent_summary", {}) or {}),
            "active_consent_policy": SimpleLazyObject(_lazy_active_policy),
            "consent_cookie_name": getattr(settings, "CONSENT_COOKIE_NAME", "consent_status"),
            "consent_cookie_secure": bool(
                getattr(settings, "CONSENT_COOKIE_SECURE", not getattr(settings, "DEBUG", False))
            ),
            "consent_cookie_samesite": getattr(
                settings, "CONSENT_COOKIE_SAMESITE", "Lax"
            ),
            "consent_cookie_max_age": int(
                getattr(settings, "CONSENT_COOKIE_MAX_AGE", 31536000
            )),
        }

        return ctx

    except Exception as exc:
        logger.exception("Consent context processor failed: %s", exc)
        return {
            "has_cookie_consent": False,
            "cookie_consent_categories": {"functional": True},
            "consent_categories": {
                "functional": {"checked": True, "required": True, "name": "functional"}
            },
            "consent_version": None,
            "consent_summary": {},
            "active_consent_policy": None,
            "consent_cookie_name": "consent_status",
            "consent_cookie_secure": False,
            "consent_cookie_samesite": "Lax",
            "consent_cookie_max_age": 31536000,
        }
