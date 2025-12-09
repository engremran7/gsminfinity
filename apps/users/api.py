
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse, HttpRequest
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import Notification
from .services.rate_limit import allow_action


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
            "url": getattr(n, "url", None),
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in qs
    ]
    return JsonResponse({"items": items})


@require_POST
def password_reset_verify(request: HttpRequest) -> JsonResponse:
    """
    Verify a password-reset code (token) inline and return the reset URL.
    This allows signed-in users to paste the code without clicking the email link.
    """
    email = (request.POST.get("email") or "").strip().lower()
    code = (request.POST.get("code") or "").strip()

    if not email or not code:
        return JsonResponse({"ok": False, "error": "Email and code are required."}, status=400)

    # Per-IP/email throttle to prevent enumeration/guessing.
    rl_key = f"pwreset_verify:{request.META.get('REMOTE_ADDR', 'unknown')}:{email}"
    if not allow_action(rl_key, max_attempts=5, window_seconds=300):
        return JsonResponse({"ok": False, "error": "Too many attempts. Try again later."}, status=429)

    user = get_user_model().objects.filter(email__iexact=email).first()
    if not user:
        # Generic response to avoid user enumeration
        return JsonResponse({"ok": False, "error": "Invalid or expired code."}, status=400)

    if not default_token_generator.check_token(user, code):
        return JsonResponse({"ok": False, "error": "Invalid or expired code."}, status=400)

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    reset_url = reverse("account_reset_password_from_key", args=[uidb64, code])
    return JsonResponse({"ok": True, "redirect": reset_url})


