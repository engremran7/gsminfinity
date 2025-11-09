"""
Unified Enterprise URL Configuration for GSMInfinity (Final Production-Ready)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

# -------------------------------------------------------------------
# Public / Core Views
# -------------------------------------------------------------------
from apps.core import views as core_views


# -------------------------------------------------------------------
# Admin Branding
# -------------------------------------------------------------------
admin.site.site_header = "GSM Admin Panel"
admin.site.site_title = "GSM Admin"
admin.site.index_title = "Site Administration"


# -------------------------------------------------------------------
# URL Patterns
# -------------------------------------------------------------------
urlpatterns = [
    # ---------------------------------------------------------------
    # Admin Panel
    # ---------------------------------------------------------------
    path("admin/", admin.site.urls),

    # ---------------------------------------------------------------
    # Authentication (Allauth)
    # /accounts/login/, /accounts/signup/, /accounts/social/
    # ---------------------------------------------------------------
    path("accounts/", include("allauth.urls")),

    # ---------------------------------------------------------------
    # Modular Apps (namespaced includes)
    # ---------------------------------------------------------------
    path("users/", include(("apps.users.urls", "users"), namespace="users")),
    path("consent/", include(("apps.consent.urls", "consent"), namespace="consent")),
    path("settings/", include(("apps.site_settings.urls", "site_settings"), namespace="site_settings")),
    path("core/", include(("apps.core.urls", "core"), namespace="core")),

    # ---------------------------------------------------------------
    # Root Landing Page
    # ---------------------------------------------------------------
    path("", core_views.home, name="home"),

    # ---------------------------------------------------------------
    # Tenant & Multi-site entrypoint (optional direct mapping)
    # ---------------------------------------------------------------
    path("tenants/", core_views.tenants, name="tenants"),

    # ---------------------------------------------------------------
    # Legacy & Convenience Redirects
    # ---------------------------------------------------------------
    path("index/", RedirectView.as_view(pattern_name="home", permanent=True)),
]


# -------------------------------------------------------------------
# Static & Media (Development Only)
# -------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# -------------------------------------------------------------------
# Custom Error Handlers (Global)
# -------------------------------------------------------------------
handler404 = "apps.core.views.error_404_view"
handler403 = "apps.core.views.error_403_view"
handler500 = "apps.core.views.error_500_view"


# -------------------------------------------------------------------
# Optional: Admin Redirect for root-level /admin (security-friendly)
# -------------------------------------------------------------------
# Uncomment to redirect /admin to /admin/login if not authenticated
# from django.contrib.auth.decorators import login_required
# admin.site.login = login_required(admin.site.login)
