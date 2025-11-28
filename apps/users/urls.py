"""
apps.users.urls
================
Enterprise-grade URL configuration for GSMInfinity Users module.
"""

from allauth.account.views import LogoutView
from django.urls import path

from . import api, views_notifications
from .views import (
    EnterpriseLoginView,
    EnterpriseSignupView,
    auth_hub_view,
    change_username,
    dashboard_view,
    device_list_view,
    device_reset_view,
    profile_view,
    resend_verification,
    tell_us_about_you,
    verify_email_view,
)

app_name = "users"

urlpatterns = [
    path("auth/", auth_hub_view, name="auth_hub"),
    path("login/", EnterpriseLoginView.as_view(), name="account_login"),
    path("signup/", EnterpriseSignupView.as_view(), name="account_signup"),
    path("logout/", LogoutView.as_view(), name="account_logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", profile_view, name="profile"),
    path("devices/", device_list_view, name="devices"),
    path("devices/<int:pk>/reset/", device_reset_view, name="device_reset"),
    path("verify-email/", verify_email_view, name="verify_email"),
    path("tell-us-about-you/", tell_us_about_you, name="tell_us_about_you"),
    path("accounts/resend-verification/", resend_verification, name="resend_verification"),
    path("accounts/change-username/", change_username, name="change_username"),
    path("notifications/unread.json", api.notifications_unread_json, name="notifications_unread_json"),
    path("notifications/", views_notifications.notification_list, name="notifications"),
    path("notifications/<int:pk>/", views_notifications.notification_detail, name="notification_detail"),
    path("notifications/mark-all/", views_notifications.notification_mark_all_read, name="notification_mark_all"),
]
