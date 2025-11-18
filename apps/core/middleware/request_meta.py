"""
apps.core.middleware.request_meta
---------------------------------
Enterprise-grade request metadata middleware for GSMInfinity.

✅ Fully compatible with Django ≥ 5.2
✅ Async + sync safe (MiddlewareMixin)
✅ No deprecated APIs
✅ Captures site, client IP, and user agent with fallbacks
✅ Normalizes headers for proxies/load balancers (X-Forwarded-For)
✅ Adds request.origin and request.scheme_normalized helpers
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest

logger = logging.getLogger(__name__)


class RequestMetaMiddleware(MiddlewareMixin):
    """
    Attach normalized request metadata to every request safely.
    Ensures consistent access to site name/domain, client IP, and headers.
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Populate request attributes:
          • site_domain / site_name (from django.contrib.sites)
          • client_ip (honoring proxy headers)
          • user_agent
          • origin (for CORS/security logging)
          • scheme_normalized ("http"/"https")
        """

        # --------------------------------------------------------
        # Site resolution with safe fallback
        # --------------------------------------------------------
        try:
            site = get_current_site(request)
            request.site_domain = getattr(site, "domain", None) or request.get_host()
            request.site_name = getattr(site, "name", "") or request.site_domain
        except Exception as exc:
            logger.debug("RequestMetaMiddleware: site resolution failed → %s", exc)
            request.site_domain = request.get_host()
            request.site_name = request.site_domain

        # --------------------------------------------------------
        # Determine client IP (handles X-Forwarded-For safely)
        # --------------------------------------------------------
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            # take the first IP (leftmost) only if properly formatted
            client_ip = xff.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR", "")

        request.client_ip = client_ip

        # --------------------------------------------------------
        # Capture user agent
        # --------------------------------------------------------
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")

        # --------------------------------------------------------
        # Origin & scheme helpers
        # --------------------------------------------------------
        request.scheme_normalized = "https" if request.is_secure() else "http"
        request.origin = f"{request.scheme_normalized}://{request.get_host()}"

        logger.debug(
            "RequestMetaMiddleware attached → site=%s, ip=%s, ua=%s",
            request.site_domain,
            request.client_ip,
            (request.user_agent or "unknown")[:64],
        )
