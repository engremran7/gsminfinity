from __future__ import annotations

import logging
from typing import Any

from .models import SecurityEvent

logger = logging.getLogger(__name__)


def emit_security_event(
    event_type: str,
    user=None,
    device=None,
    ip: str | None = None,
    metadata: dict[str, Any] | None = None,
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

        # Notify user of critical security events
        if (
            user
            and getattr(user, "is_authenticated", False)
            and event_type
            in ["login_failed", "password_changed", "mfa_enabled", "mfa_disabled"]
        ):
            try:
                from apps.users.services.notifications import send_notification

                title_map = {
                    "login_failed": "Failed login attempt",
                    "password_changed": "Password changed",
                    "mfa_enabled": "MFA enabled",
                    "mfa_disabled": "MFA disabled",
                }

                msg_map = {
                    "login_failed": f"A failed login attempt was detected from {ip or 'unknown IP'}.",
                    "password_changed": "Your password was recently changed.",
                    "mfa_enabled": "Two-factor authentication was enabled on your account.",
                    "mfa_disabled": "Two-factor authentication was disabled on your account.",
                }

                send_notification(
                    recipient=user,
                    title=title_map.get(event_type, "Security Alert"),
                    message=msg_map.get(
                        event_type, "A security event occurred on your account."
                    ),
                    level="warning" if event_type == "login_failed" else "info",
                    channel="web",
                    action_type="security",
                    icon="shield",
                )
            except Exception:
                pass

    except Exception as exc:  # pragma: no cover - defensive path
        logger.debug("emit_security_event skipped: %s", exc)
        return
