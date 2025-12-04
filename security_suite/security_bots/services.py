"""
security_bots.services

Shim that delegates to the existing crawler_guard app while we migrate.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from . import conf

logger = logging.getLogger(__name__)


def is_suspicious(request) -> bool:
    if not conf.get("ENABLED", True):
        return False
    try:
        from apps.crawler_guard.middleware import classify as _classify  # type: ignore

        verdict = _classify(request)
        return bool(getattr(verdict, "is_suspicious", False) or getattr(verdict, "blocked", False))
    except Exception as exc:
        logger.debug("security_bots: is_suspicious fallback (%s)", exc)
        return False


def classify_request(request) -> Dict[str, Any]:
    if not conf.get("ENABLED", True):
        return {"label": "unknown", "action": conf.get("DEFAULT_ACTION", "allow")}
    try:
        from apps.crawler_guard.middleware import classify as _classify  # type: ignore

        verdict = _classify(request)
        return {
            "label": getattr(verdict, "label", "unknown"),
            "action": getattr(verdict, "action", conf.get("DEFAULT_ACTION", "allow")),
            "is_suspicious": bool(getattr(verdict, "is_suspicious", False)),
        }
    except Exception as exc:
        logger.debug("security_bots: classify_request fallback (%s)", exc)
        return {"label": "unknown", "action": conf.get("DEFAULT_ACTION", "allow")}
