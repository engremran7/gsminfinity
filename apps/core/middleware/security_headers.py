"""
apps.core.middleware.security_headers
====================================

Enterprise-grade security header middleware.

✅ Django 5.2+ / Python 3.12+
✅ Per-request CSP nonces (no 'unsafe-inline')
✅ Compatible with modern browsers / COOP / CORP
✅ Minimal overhead (nonce generated once per request)
✅ Logging-aware, no silent leaks
"""

from __future__ import annotations

import logging
import secrets
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

DEFAULT_HSTS = "max-age=63072000; includeSubDomains; preload"
DEFAULT_COEP = "require-corp"
DEFAULT_CORP = "same-origin"


class SecurityHeadersMiddleware:
    """Attach enterprise-grade secure HTTP headers to each response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.hsts_value = getattr(settings, "SECURITY_HSTS_VALUE", DEFAULT_HSTS)
        self.coep_value = getattr(settings, "SECURITY_COEP_VALUE", DEFAULT_COEP)
        self.corp_value = getattr(settings, "SECURITY_CORP_VALUE", DEFAULT_CORP)
        # Log once at startup for visibility
        logger.info(
            "SecurityHeadersMiddleware initialized (DEBUG=%s)",
            getattr(settings, "DEBUG", False),
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Create per-request nonce (used in inline scripts/styles if templates add it)
        nonce = secrets.token_urlsafe(16)
        setattr(request, "csp_nonce", nonce)

        response = self.get_response(request)

        # ------------------------------------------------------------------
        # Core modern security headers
        # ------------------------------------------------------------------
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response["Cross-Origin-Resource-Policy"] = self.corp_value
        response["Cross-Origin-Embedder-Policy"] = self.coep_value
        response["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        # ------------------------------------------------------------------
        # Content Security Policy
        # ------------------------------------------------------------------
        # Nonce-based CSP even in DEBUG to discourage inline/eval
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://www.google.com/recaptcha/ "
            f"https://www.gstatic.com/recaptcha/; "
            f"style-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-src 'self' https://www.google.com/recaptcha/;"
        )

        response.setdefault("Content-Security-Policy", csp)

        # ------------------------------------------------------------------
        # Strict-Transport-Security (HSTS)
        # ------------------------------------------------------------------
        if not getattr(settings, "DEBUG", False) and self.hsts_value:
            is_secure = request.is_secure()
            xfp = request.META.get("HTTP_X_FORWARDED_PROTO", "")
            if is_secure or xfp.startswith("https"):
                response["Strict-Transport-Security"] = self.hsts_value

        return response
