
from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings
from apps.users.models import Notification
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


def notifications_enabled() -> bool:
    """
    Global kill-switch for notifications (UsersSettings.enable_notifications).
    Falls back to True if settings or singleton are unavailable.
    """
    try:
        from apps.users.models import UsersSettings  # local import to avoid circulars

        us = UsersSettings.get_solo()
        return bool(getattr(us, "enable_notifications", True))
    except Exception as exc:
        logger.debug("notifications_enabled fallback (default True): %s", exc)
        return True


def send_notification(
    recipient: User,
    title: str,
    message: str,
    level: str = "info",  # mapped to model.priority
    url: Optional[str] = None,
    actor: Optional[User] = None,
    channel: Optional[str] = None,  # NEW: support channel field
) -> Optional[Notification]:
    """
    Safely create a notification for a user.
    Returns the Notification instance or None on error.
    """

    if not notifications_enabled():
        return None

    if not recipient:
        return None

    try:
        with transaction.atomic():
            n = Notification.objects.create(
                recipient=recipient,
                title=title[:255],
                message=message,
                priority=level,  # FIXED: your model uses 'priority'
                channel=channel,  # NEW: support channel usage
                # created_at auto_set by model default (best practice)
            )

            # Optional: trigger websockets / signals / push
            # publish_notification(n)

            return n

    except Exception as exc:
        logger.exception(
            "Failed to create notification for user %s: %s",
            getattr(recipient, "pk", None),
            exc,
        )
        return None


def broadcast_notification(
    recipients,
    title: str,
    message: str,
    level: str = "info",
    url: Optional[str] = None,
    actor: Optional[User] = None,
    channel: Optional[str] = None,
) -> int:
    """
    Bulk-create notifications for an iterable/QuerySet of users.
    Returns count created.
    """
    if not notifications_enabled():
        return 0

    try:
        user_list = [
            r
            for r in recipients
            if r is not None and getattr(r, "is_active", True)
        ]
    except Exception as exc:
        logger.exception("broadcast_notification recipients iteration failed: %s", exc)
        return 0

    if not user_list:
        return 0

    now = timezone.now()
    payloads = [
        Notification(
            recipient=r,
            title=title[:255],
            message=message,
            priority=level,
            channel=channel,
            created_at=now,
        )
        for r in user_list
    ]

    try:
        objs = Notification.objects.bulk_create(payloads)
        return len(objs)
    except Exception as exc:
        logger.exception("broadcast_notification failed: %s", exc)
        return 0


