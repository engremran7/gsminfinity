"""
Attach common metadata to each request.
"""

import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.sites.shortcuts import get_current_site

log = logging.getLogger(__name__)

class RequestMetaMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            site = get_current_site(request)
            request.site_domain = site.domain
            request.site_name = getattr(site, "name", "")
        except Exception as exc:
            log.debug("Site resolution failed: %s", exc)
            request.site_domain = request.get_host()
        request.client_ip = request.META.get("REMOTE_ADDR", "")
        request.user_agent = request.META.get("HTTP_USER_AGENT", "")
