from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.users.services.rate_limit import allow_action
from apps.core.utils.ip import get_client_ip

logger = logging.getLogger(__name__)


class PasswordResetThrottleMiddleware(MiddlewareMixin):
    """
    Tight throttle for password reset initiation to prevent email spam and abuse.
    Applies to POST /accounts/password/reset/.
    """

    def process_view(self, request: HttpRequest, view_func, view_args, view_kwargs):
        if request.method.lower() != "post":
            return None

        path = request.path.lower().rstrip("/")
        if not path.endswith("/accounts/password/reset"):
            return None

        email = (request.POST.get("email") or "").strip().lower()
        client_ip = get_client_ip(request) or "unknown"
        per_combo_key = f"pwreset_init:{client_ip}:{email or 'noemail'}"
        per_email_key = f"pwreset_email:{email or 'noemail'}"
        per_ip_key = f"pwreset_ip:{client_ip}"

        allowed = True
        try:
            # Tight IP+email throttle
            if not allow_action(per_combo_key, max_attempts=3, window_seconds=300):
                allowed = False
            # Per-email longer window to prevent cross-IP spamming
            if allowed and not allow_action(per_email_key, max_attempts=10, window_seconds=3600):
                allowed = False
            # Per-IP global guard
            if allowed and not allow_action(per_ip_key, max_attempts=10, window_seconds=900):
                allowed = False
        except Exception as exc:
            logger.warning("Reset throttle backend failure: %s", exc)
            allowed = True

        if not allowed:
            if request.headers.get("Accept", "").startswith("application/json"):
                return JsonResponse(
                    {"ok": False, "error": "Too many reset attempts. Try again in a few minutes."},
                    status=429,
                )
            return HttpResponse("Too many reset attempts. Try again in a few minutes.", status=429)

        return None
