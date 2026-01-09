"""
apps.consent package initializer.
Fails fast on API import errors outside test/CI to avoid silent misconfiguration.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def __getattr__(name: str):
    if name in {"get_consent_status", "update_consent"}:
        try:
            from apps.consent.api.views import get_consent_status, update_consent

            return {
                "get_consent_status": get_consent_status,
                "update_consent": update_consent,
            }[name]
        except Exception as exc:  # pragma: no cover
            logger.critical("Consent API import failure: %s", exc, exc_info=True)
            if os.getenv("DJANGO_ENV") not in {"test", "ci", "development"}:
                raise
            return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
