from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .models import SecurityEvent

logger = logging.getLogger(__name__)


def emit_security_event(
    event_type: str,
    user=None,
    device=None,
    ip: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Best-effort event emitter for security-related activities.
    Safe to call even if migrations are not yet applied.
    """
    try:
        SecurityEvent.objects.create(
            type=event_type,
            user=user if getattr(user, "is_authenticated", False) else None,
            device=device,
            ip=ip,
            metadata=metadata or {},
        )
    except Exception as exc:  # pragma: no cover - defensive path
        logger.debug("emit_security_event skipped: %s", exc)
        return
