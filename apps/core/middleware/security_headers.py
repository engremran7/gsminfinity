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

import secrets
import logging
from typing import Callable
from django.conf import settings
from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Attach enterprise-grade secure HTTP headers to each response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        # Log once at startup for visibility
        logger.info(
            "SecurityHeadersMiddleware initialized (DEBUG=%s)", getattr(settings, "DEBUG", False)
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
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response["Cross-Origin-Embedder-Policy"] = "require-corp"
        response["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        # ------------------------------------------------------------------
        # Content Security Policy
        # ------------------------------------------------------------------
        if getattr(settings, "DEBUG", False):
            # Developer-friendly CSP (still restrictive)
            csp = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss:; frame-src 'self';"
            )
        else:
            # Production CSP: strict, nonce-based, no unsafe-inline/eval
            csp = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' https://www.google.com/recaptcha/ "
                f"https://www.gstatic.com/recaptcha/; "
                f"style-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "frame-src 'self' https://www.google.com/recaptcha/;"
            )

        response.setdefault("Content-Security-Policy", csp)

        # ------------------------------------------------------------------
        # Strict-Transport-Security (HSTS)
        # ------------------------------------------------------------------
        if not getattr(settings, "DEBUG", False):
            # 2 years = 63072000 s, include subdomains, preload
            response["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
