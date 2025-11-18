# apps/core/middleware/ssl_toggle.py
"""
apps/core/middleware/ssl_toggle
===============================
Dynamic HTTPS Enforcement Middleware for GSMInfinity.

✅ Safe across all environments
✅ Controlled by SiteSettings.force_https (admin-managed)
✅ Can be globally disabled via ENV variable FORCE_HTTPS_DEV_OVERRIDE
✅ Compatible with Django 5.2+
✅ No deprecations or recursion risks
"""

from __future__ import annotations
import os
import logging
from typing import Optional
from django.http import HttpRequest, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


def _should_force_https() -> bool:
    """
    Runtime-safe evaluation of SiteSettings.force_https.
    - Returns False on any import/config errors.
    - Can be overridden via the env var FORCE_HTTPS_DEV_OVERRIDE=0.
    """
    override = os.getenv("FORCE_HTTPS_DEV_OVERRIDE")
    if override is not None and override.strip().lower() in ("0", "false", "off", "no"):
        return False

    try:
        from apps.site_settings.models import SiteSettings  # local import
        settings_obj = SiteSettings.get_solo()
        return bool(getattr(settings_obj, "force_https", False))
    except Exception as e:
        logger.debug(f"[SslToggle] Fallback to HTTP: {e}")
        return False


class SslToggleMiddleware(MiddlewareMixin):
    """
    Middleware to redirect HTTP -> HTTPS only when:
      1. The current request is insecure, AND
      2. SiteSettings.force_https == True, AND
      3. FORCE_HTTPS_DEV_OVERRIDE is not disabling enforcement.
    """

    def process_request(self, request: HttpRequest) -> Optional[HttpResponseRedirect]:
        # Skip if already HTTPS or behind secure proxy
        if request.is_secure() or request.META.get("HTTP_X_FORWARDED_PROTO") == "https":
            return None

        if _should_force_https():
            absolute = request.build_absolute_uri(request.get_full_path())
            if absolute.startswith("http://"):
                https_url = "https://" + absolute[len("http://") :]
                logger.info(f"[SslToggle] Redirecting to HTTPS: {https_url}")
                return HttpResponseRedirect(https_url)

        return None
