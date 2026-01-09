"""
apps.core.middleware.request_meta
---------------------------------
Enterprise-grade request metadata middleware for GSMInfinity.

- Fully compatible with Django 5.2+
- Async + sync safe (modern middleware)
- Captures site, client IP, and user agent with fallbacks
- Normalizes headers for proxies/load balancers (X-Forwarded-For)
- Adds request.origin and request.scheme_normalized helpers
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest, HttpResponse

from apps.core.utils.ip import get_client_ip

logger = logging.getLogger(__name__)


class RequestMetaMiddleware:
    """Attach normalized request metadata to every request safely."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Populate request attributes:
          - site_domain / site_name (from django.contrib.sites)
          - client_ip (honoring proxy headers)
          - user_agent
          - origin (for CORS/security logging)
          - scheme_normalized ("http"/"https")
        """
        self._attach_metadata(request)
        return self.get_response(request)

    def _attach_metadata(self, request: HttpRequest) -> None:
        # Site resolution with safe fallback
        try:
            site = get_current_site(request)
            request.site_domain = getattr(site, "domain", None) or request.get_host()
            request.site_name = getattr(site, "name", "") or request.site_domain
        except Exception as exc:
            logger.debug("RequestMetaMiddleware: site resolution failed - %s", exc)
            request.site_domain = request.get_host()
            request.site_name = request.site_domain

        # Determine client IP via centralized helper
        request.client_ip = get_client_ip(request)

        # Capture user agent
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Origin & scheme helpers
        request.scheme_normalized = "https" if request.is_secure() else "http"
        request.origin = f"{request.scheme_normalized}://{request.get_host()}"

        logger.debug(
            "RequestMetaMiddleware attached - site=%s, ip=%s, ua=%s",
            request.site_domain,
            request.client_ip,
            (request.user_agent or "unknown")[:64],
        )
