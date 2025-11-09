# apps/core/urls.py
from django.urls import path
from . import views

# ============================================================
#  Core Application URL Configuration
# ============================================================
urlpatterns = [
    # --------------------------------------------------------
    #  Home / Landing
    # --------------------------------------------------------
    path("", views.home, name="home"),

    # --------------------------------------------------------
    #  Tenants (Multi-Site Overview)
    # --------------------------------------------------------
    path("tenants/", views.tenants, name="tenants"),

    # --------------------------------------------------------
    #  Dashboard Routes
    # --------------------------------------------------------
    path("dashboard/", views.overview, name="dashboard_overview"),
    path("dashboard/security/", views.security, name="dashboard_security"),
    path("dashboard/monetization/", views.monetization, name="dashboard_monetization"),
    path("dashboard/notifications/", views.notifications, name="dashboard_notifications"),
    path("dashboard/announcements/", views.announcements, name="dashboard_announcements"),
    path("dashboard/users/", views.users_dashboard, name="dashboard_users"),
    path("dashboard/system/", views.system_health, name="dashboard_system"),
]

# ============================================================
#  Notes:
#  - All paths are mapped to view functions in apps.core.views
#  - URL names are namespaced consistently for template reverse lookups
#  - Extend this file when adding new dashboard or core sections
# ============================================================
