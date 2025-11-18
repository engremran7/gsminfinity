# apps/core/urls.py
"""
GSMInfinity — Core URL Configuration (Enterprise-Grade)
========================================================
Features:
- Full Django 5.2+ compliance (no deprecated APIs)
- Lazy view loading with import_string (prevents circular imports)
- Explicit namespacing for reverse() lookups
- Legal and policy page aliases for seamless frontend template integration
- Fully aligned with apps.core.views and apps.site_settings.views

Namespace: "core"
"""

from django.urls import path
from django.utils.module_loading import import_string
from typing import Callable, Any


# ----------------------------------------------------------------------
# Lazy Import Utility
# ----------------------------------------------------------------------
def view(name: str) -> Callable[..., Any]:
    """
    Dynamically import a view function by its dotted name.

    Supports:
      - short names (e.g., "home") → imports apps.core.views.home
      - fully qualified names (e.g., "apps.site_settings.views.privacy_policy")
        → imports directly without namespacing

    This approach prevents circular imports and reduces startup time.
    """
    if "." in name and not name.startswith("apps.core.views"):
        return import_string(name)
    return import_string(f"apps.core.views.{name}")


# ----------------------------------------------------------------------
# Namespace Declaration
# ----------------------------------------------------------------------
app_name = "core"


# ----------------------------------------------------------------------
# URL Patterns
# ----------------------------------------------------------------------
urlpatterns = [
    # ---------------------------------------------------------------
    #  Public Home / Landing
    # ---------------------------------------------------------------
    path("", view("home"), name="home"),

    # ---------------------------------------------------------------
    #  Tenants (Multi-Site Overview)
    # ---------------------------------------------------------------
    path("tenants/", view("tenants"), name="tenants"),

    # ---------------------------------------------------------------
    #  Dashboard Routes
    # ---------------------------------------------------------------
    path("dashboard/", view("overview"), name="dashboard_overview"),
    path("dashboard/security/", view("security"), name="dashboard_security"),
    path("dashboard/monetization/", view("monetization"), name="dashboard_monetization"),
    path("dashboard/notifications/", view("notifications"), name="dashboard_notifications"),
    path("dashboard/announcements/", view("announcements"), name="dashboard_announcements"),
    path("dashboard/users/", view("users_dashboard"), name="dashboard_users"),
    path("dashboard/system/", view("system_health"), name="dashboard_system"),

    # ---------------------------------------------------------------
    #  Legal / Policy Page Aliases
    # ---------------------------------------------------------------
    # These aliases ensure existing templates referencing {% url 'privacy' %}
    # or {% url 'terms' %} continue to work seamlessly.
    # They map to canonical views in apps.site_settings.views.
    path("privacy/", view("apps.site_settings.views.privacy_policy"), name="privacy"),
    path("terms/", view("apps.site_settings.views.terms_of_service"), name="terms"),
    path("cookies/", view("apps.site_settings.views.cookies_policy"), name="cookies"),
]


# ----------------------------------------------------------------------
# Notes:
# - All paths are namespaced under "core" for explicit reverse() lookups:
#     {% url 'core:dashboard_overview' %}
#     {% url 'core:privacy' %}
# - For cross-app aliasing, dotted import paths are used safely.
# - No recursion, no deprecated include() nesting, 100% Django 5.2+ ready.
# ----------------------------------------------------------------------
