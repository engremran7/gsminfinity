"""
apps.users.urls
================
Enterprise-grade URL configuration for GSMInfinity Users module.

✅ Features:
- Unified authentication hub (login / signup / social)
- EnterpriseLoginView & EnterpriseSignupView integration
- Logout via allauth
- Verified dashboard + profile routes
- Explicit namespacing for template reverse() safety
- Email verification flow

Fully compatible with Django 5.x / django-allauth ≥ 0.65.
"""

from django.urls import path
from allauth.account.views import LogoutView

from .views import (
    auth_hub_view,
    dashboard_view,
    profile_view,
    verify_email_view,
    EnterpriseLoginView,
    EnterpriseSignupView,
)

app_name = "users"

urlpatterns = [
    # ------------------------------------------------------------------
    # 🔐 Unified Authentication Hub
    # ------------------------------------------------------------------
    path("auth/", auth_hub_view, name="auth_hub"),

    # ------------------------------------------------------------------
    # 🧭 Authentication (Allauth-based)
    # ------------------------------------------------------------------
    path("login/", EnterpriseLoginView.as_view(), name="account_login"),
    path("signup/", EnterpriseSignupView.as_view(), name="account_signup"),
    path("logout/", LogoutView.as_view(), name="account_logout"),

    # ------------------------------------------------------------------
    # 👤 User Dashboard & Profile
    # ------------------------------------------------------------------
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", profile_view, name="profile"),

    # ------------------------------------------------------------------
    # ✉️  Email Verification
    # ------------------------------------------------------------------
    path("verify-email/", verify_email_view, name="verify_email"),
]

# ----------------------------------------------------------------------
# Notes:
# - All view classes / functions live in apps.users.views
# - All URLs are namespaced ("users:...") for reverse resolution
# - Safe to include under project-level /users/ route
# ----------------------------------------------------------------------
