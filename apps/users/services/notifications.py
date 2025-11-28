from __future__ import annotations

import logging
from typing import Optional

from apps.users.models import Notification
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


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

    try:
        with transaction.atomic():
            n = Notification.objects.create(
                recipient=recipient,
                title=title[:255],
                message=message,
                priority=level,  # FIXED: your model uses 'priority'
                url=url or "",
                actor=actor,
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