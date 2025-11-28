"""
apps.core.middleware.rate_limit_bridge
--------------------------------------
Bridges Django requests to apps.users.services.rate_limit.allow_action().
Prevents brute-force login/signup attempts globally.
"""

import logging

from apps.users.services import rate_limit
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Attach global rate limit for login/signup endpoints."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower()

        if "login" in path or "signup" in path:
            client_ip = self._get_client_ip(request)
            key = f"auth:{client_ip}:{path}"

            # 10 attempts / 5 minutes window
            allowed = rate_limit.allow_action(key, max_attempts=10, window_seconds=300)
            if not allowed:
                logger.warning(f"Rate limit exceeded for {client_ip} at {path}")
                return JsonResponse(
                    {
                        "error": "Too many attempts. Please wait a few minutes before retrying."
                    },
                    status=429,
                )

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")