"""
Users App – URL Configuration
---------------------------------------
Routes for authentication, onboarding, and user dashboards.

Integrates tightly with django-allauth ≥0.65 and GSMInfinity's
custom enterprise user management flow.
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
    # ---------------------------------------------------------------
    # Unified Auth Hub (Landing page for login/signup/social)
    # ---------------------------------------------------------------
    path("auth/", auth_hub_view, name="auth_hub"),

    # ---------------------------------------------------------------
    # Authentication (Allauth Overrides)
    # ---------------------------------------------------------------
    path("login/", EnterpriseLoginView.as_view(), name="account_login"),
    path("signup/", EnterpriseSignupView.as_view(), name="account_signup"),
    path("logout/", LogoutView.as_view(), name="account_logout"),

    # ---------------------------------------------------------------
    # User Dashboard & Profile
    # ---------------------------------------------------------------
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", profile_view, name="profile"),

    # ---------------------------------------------------------------
    # Email Verification
    # ---------------------------------------------------------------
    path("verify-email/", verify_email_view, name="verify_email"),
]
