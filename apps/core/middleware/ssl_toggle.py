# apps/core/middleware/ssl_toggle.py
"""
apps/core/middleware/ssl_toggle
===============================
Dynamic HTTPS enforcement driven by SiteSettings.force_https with safe dev defaults.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect

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
    except Exception as exc:
        logger.debug("[SslToggle] Fallback to HTTP: %s", exc)
        return False


class SslToggleMiddleware:
    """
    Middleware to redirect HTTP -> HTTPS only when:
      1. The current request is insecure, AND
      2. SiteSettings.force_https == True, AND
      3. FORCE_HTTPS_DEV_OVERRIDE is not disabling enforcement, AND
      4. settings.DEBUG is False.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        redirect_response = self._maybe_redirect(request)
        if redirect_response is not None:
            return redirect_response
        return self.get_response(request)

    def _maybe_redirect(self, request: HttpRequest) -> Optional[HttpResponse]:
        # Never interfere with local/dev debugging
        try:
            if getattr(settings, "DEBUG", False):
                return None
        except Exception:
            # If settings is weirdly inaccessible, fail open.
            return None

        # Already secure -> nothing to do
        if request.is_secure():
            return None

        # Respect SiteSettings + env override
        if not _should_force_https():
            return None

        # Only redirect idempotent methods (avoid breaking POST/PUT forms)
        if request.method not in ("GET", "HEAD"):
            return None

        # Build HTTPS URL preserving path + querystring
        host = request.get_host()
        path = request.get_full_path()
        url = f"https://{host}{path}"

        logger.debug("[SslToggle] Redirecting to HTTPS: %s", url)
        return HttpResponseRedirect(url)
