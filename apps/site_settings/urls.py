"""
Site settings URLs: diagnostics + verification only.
Public policy pages are served by apps.pages.
"""

from django.urls import path

from . import views

app_name = "site_settings"

urlpatterns = [
    path("", views.site_settings_view, name="site_settings"),
    path("info/", views.settings_info, name="settings_info"),
    path(
        "verification/<str:filename>/",
        views.verification_file,
        name="verification_file",
    ),
    # Legacy legal aliases -> redirect to pages app if present
    path(
        "privacy/",
        views.legacy_privacy_redirect,
        name="privacy_policy",
    ),
    path(
        "terms/",
        views.legacy_terms_redirect,
        name="terms_of_service",
    ),
    path(
        "cookies/",
        views.legacy_cookies_redirect,
        name="cookies_policy",
    ),
]
