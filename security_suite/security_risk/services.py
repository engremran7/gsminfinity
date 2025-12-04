"""
security_risk.services

Shim that delegates to the existing ai_behavior app while we migrate.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from . import conf

logger = logging.getLogger(__name__)


def get_current_risk(request=None, user=None) -> Dict[str, Any]:
    if not conf.get("ENABLED", True):
        return {"score": 0, "level": "none", "reasons": []}
    try:
        from apps.ai_behavior.services import get_current_risk as _get_risk  # type: ignore

        return _get_risk(request=request, user=user)
    except Exception as exc:
        logger.debug("security_risk: get_current_risk fallback (%s)", exc)
        return {"score": 0, "level": "none", "reasons": []}


def record_event(event_type: str, request=None, user=None, metadata: Optional[Dict[str, Any]] = None):
    if not conf.get("ENABLED", True):
        return
    try:
        from apps.ai_behavior.services import record_event as _record  # type: ignore

        _record(event_type=event_type, request=request, user=user, metadata=metadata)
    except Exception as exc:
        logger.debug("security_risk: record_event skipped (%s)", exc)
        return
