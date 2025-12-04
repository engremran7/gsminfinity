
"""
apps.site_settings.urls
Unified routing for GSMInfinity Site Settings module.

✓ Django 5.2+ Ready
✓ Namespaced under `site_settings`
✓ Safe, cache-friendly routing
✓ Aligned with actual available view functions
✓ No duplication, no dead routes
"""

from django.urls import path

from . import views

app_name = "site_settings"


urlpatterns = [
    # ---------------------------------------------------------------------
    # 🌐 Public Diagnostic / Admin-facing HTML View
    # ---------------------------------------------------------------------
    path(
        "",
        views.site_settings_view,
        name="site_settings",
    ),  # Admin diagnostic readable settings page
    # ---------------------------------------------------------------------
    # 🔧 JSON API for Frontend Bootstrapping
    # ---------------------------------------------------------------------
    path(
        "info/",
        views.settings_info,
        name="settings_info",
    ),
    # ---------------------------------------------------------------------
    # 🔐 Domain Verification Files (Google / Apple / Facebook)
    # ---------------------------------------------------------------------
    path(
        "verification/<str:filename>/",
        views.verification_file,
        name="verification_file",
    ),
    # ---------------------------------------------------------------------
    # 📜 Public Policy & Legal Pages (GDPR Compliant)
    # ---------------------------------------------------------------------
    path(
        "privacy/",
        views.privacy_policy,
        name="privacy_policy",
    ),
    path(
        "terms/",
        views.terms_of_service,
        name="terms_of_service",
    ),
    path(
        "cookies/",
        views.cookies_policy,
        name="cookies_policy",
    ),
]

