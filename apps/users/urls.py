
"""
apps.users.urls
Enterprise-grade URL configuration for GSMInfinity Users module.
"""

from allauth.account.views import LogoutView
from django.urls import path

from . import api, views_notifications, admin_views
from .views import (
    EnterpriseLoginView,
    EnterpriseSignupView,
    auth_hub_view,
    change_username,
    check_username,
    dashboard_view,
    profile_view,
    devices_view,
    resend_verification,
    tell_us_about_you,
    verify_email_view,
    verify_email_status,
    device_approval_needed,
    approve_device,
    device_eviction,
    device_mfa_challenge,
    notification_settings,
    push_subscription,
    unsubscribe_push,
)

app_name = "users"

urlpatterns = [
    path("auth/", auth_hub_view, name="auth_hub"),
    path("login/", EnterpriseLoginView.as_view(), name="account_login"),
    path("signup/", EnterpriseSignupView.as_view(), name="account_signup"),
    path("logout/", LogoutView.as_view(), name="account_logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", profile_view, name="profile"),
    path("devices/", devices_view, name="devices"),
    path("devices/approval/", device_approval_needed, name="device_approval_needed"),
    path("devices/approve/", approve_device, name="approve_device"),
    path("devices/evict/", device_eviction, name="device_eviction"),
    path("devices/mfa/", device_mfa_challenge, name="device_mfa_challenge"),
    path("verify-email/", verify_email_view, name="verify_email"),
    path("verify-email/status/", verify_email_status, name="verify_email_status"),
    path("tell-us-about-you/", tell_us_about_you, name="tell_us_about_you"),
    path("accounts/resend-verification/", resend_verification, name="resend_verification"),
    path("accounts/change-username/", change_username, name="change_username"),
    path("accounts/check-username/", check_username, name="check_username"),
    path("notifications/unread.json", api.notifications_unread_json, name="notifications_unread_json"),
    path("notifications/", views_notifications.notification_list, name="notifications"),
    path("notifications/<int:pk>/", views_notifications.notification_detail, name="notification_detail"),
    path("notifications/mark-all/", views_notifications.notification_mark_all_read, name="notification_mark_all"),
    path("notifications/settings/", notification_settings, name="notification_settings"),
    path("notifications/push/subscribe/", push_subscription, name="push_subscription"),
    path("notifications/push/unsubscribe/", unsubscribe_push, name="unsubscribe_push"),
    path("admin/notification-dashboard/", admin_views.notification_dashboard, name="notification_dashboard"),
    path("api/password-reset/verify/", api.password_reset_verify, name="password_reset_verify"),
]

# Admin API endpoints (add to main admin URLconf via gsminfinity/urls.py)
admin_api_patterns = [
    path("admin/users/notification/stats/", api.notification_stats, name="notification_stats_api"),
]

urlpatterns += admin_api_patterns


