"""
Unified Enterprise URL Configuration for the project.

Production-ready for:
  • Django 5.2+
  • Python 3.12+
  • django-allauth 0.65+

Features:
  - Async-safe lazy loader
  - Modular routing (users, notifications under users, consent, site_settings, core)
  - Static & media (dev only)
  - Health endpoint
  - Hardened admin identity (non-branded)
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.utils.module_loading import import_string
from django.views.generic import RedirectView

logger = logging.getLogger(__name__)


# =====================================================================
# Async-safe lazy view importer
# =====================================================================
def lazy_view(dotted_path: str) -> Callable[..., Any]:
    """
    Import view lazily at call time.
    Supports sync, async, and class-based views.
    """

    async def _wrapper(request, *args, **kwargs):
        view_obj = import_string(dotted_path)

        # Class-based view support
        if inspect.isclass(view_obj) and hasattr(view_obj, "as_view"):
            view_callable = view_obj.as_view()
        else:
            view_callable = view_obj

        result = view_callable(request, *args, **kwargs)

        # Async view support
        if inspect.isawaitable(result):
            return await result
        return result

    return _wrapper


# =====================================================================
# Admin Branding (non-branded; project rule)
# =====================================================================
admin.site.site_header = "Administration"
admin.site.site_title = "Admin Portal"
admin.site.index_title = "System Management Console"


# =====================================================================
# URL Patterns
# =====================================================================
urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Authentication (allauth)
    path("accounts/", include("allauth.urls")),
    # Users module
    path("users/", include(("apps.users.urls", "users"), namespace="users")),
    # Notifications (implemented inside users app)
    # NOTE: module apps.users.notifications_urls defines app_name="users_notifications",
    # so we include it with the same internal app_name and namespace to avoid conflicts.
    path(
        "notifications/",
        include(
            ("apps.users.notifications_urls", "users_notifications"),
            namespace="users_notifications",
        ),
    ),
    # Consent subsystem
    path("consent/", include(("apps.consent.urls", "consent"), namespace="consent")),
    # Site settings
    path(
        "site_settings/",
        include(
            ("apps.site_settings.urls", "site_settings"), namespace="site_settings"
        ),
    ),
    # Core module
    path("core/", include(("apps.core.urls", "core"), namespace="core")),
    # Public root pages
    path("", lazy_view("apps.core.views.home"), name="home"),
    path("tenants/", lazy_view("apps.core.views.tenants"), name="tenants"),
    # Health check (well-known)
    path(
        ".well-known/health",
        lazy_view("apps.core.views.health_check"),
        name="health_check",
    ),
    # Legacy redirect
    path("index/", RedirectView.as_view(pattern_name="home", permanent=True)),
    # Favicon
    re_path(
        r"^favicon\.ico$",
        RedirectView.as_view(url="/static/favicon.ico", permanent=True),
    ),
]


# =====================================================================
# Static & Media (DEV only)
# =====================================================================
if settings.DEBUG:
    # media files
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        from django.contrib.staticfiles.urls import staticfiles_urlpatterns

        urlpatterns += staticfiles_urlpatterns()
    except Exception as exc:
        logger.warning("staticfiles_urlpatterns() unavailable: %s", exc)
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# =====================================================================
# Error handlers
# =====================================================================
handler400 = "apps.core.views.error_400_view"
handler403 = "apps.core.views.error_403_view"
handler404 = "apps.core.views.error_404_view"
handler500 = "apps.core.views.error_500_view"