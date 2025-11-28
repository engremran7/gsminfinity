from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest

from .models import Notification


@login_required
def notifications_unread_json(request: HttpRequest) -> JsonResponse:
    """
    Lightweight JSON endpoint for unread notifications.
    Returns up to 20 most recent unread items for header dropdowns.
    """
    qs = (
        Notification.objects.filter(recipient=request.user, is_read=False)
        .order_by("-created_at")[:20]
    )
    items = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "priority": n.priority,
            "channel": n.channel,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in qs
    ]
    return JsonResponse({"items": items})
