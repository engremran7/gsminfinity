from django.urls import path
from django.contrib.auth import views as auth_views

from apps.admin_suite import views as admin_views

app_name = "admin_suite"

urlpatterns = [
    path("login/", admin_views.AdminSuiteLoginView.as_view(), name="admin_suite_login"),
    path("login/security-question/", admin_views.admin_suite_security_question, name="admin_suite_security_question"),
    path("login/security-question/setup/", admin_views.admin_suite_security_question_setup, name="admin_suite_security_question_setup"),
    path("login/security-question/reset/", admin_views.admin_suite_password_reset, name="admin_suite_password_reset"),
    path("", admin_views.admin_suite, name="admin_suite"),
    path("command-search/", admin_views.admin_suite_command_search, name="admin_suite_command_search"),
    path("security/", admin_views.admin_suite_security, name="admin_suite_security"),
    path("security/devices/", admin_views.admin_suite_security_devices, name="admin_suite_security_devices"),
    path("security/crawlers/", admin_views.admin_suite_security_crawlers, name="admin_suite_security_crawlers"),
    path("security/risk/", admin_views.admin_suite_security_risk, name="admin_suite_security_risk"),
    path("consent/", admin_views.admin_suite_consent, name="admin_suite_consent"),
    path("pages/", admin_views.admin_suite_pages, name="admin_suite_pages"),
    path("blog/", admin_views.admin_suite_blog, name="admin_suite_blog"),
    path("content/", admin_views.admin_suite_content, name="admin_suite_content"),
    path("marketing/", admin_views.admin_suite_marketing, name="admin_suite_marketing"),
    path("ai/", admin_views.admin_suite_ai, name="admin_suite_ai"),
    path("distribution/", admin_views.admin_suite_distribution, name="admin_suite_distribution"),
    path("ads/", admin_views.admin_suite_ads, name="admin_suite_ads"),
    path("tags/", admin_views.admin_suite_tags, name="admin_suite_tags"),
    path("seo/", admin_views.admin_suite_seo, name="admin_suite_seo"),
    path("registry/", admin_views.admin_suite_registry, name="admin_suite_registry"),
    path("comments/", admin_views.admin_suite_comments, name="admin_suite_comments"),
    path("users/", admin_views.admin_suite_users, name="admin_suite_users"),
    path("users/<str:user_id>/", admin_views.admin_suite_user_detail, name="admin_suite_user_detail"),
    path("settings/", admin_views.admin_suite_settings, name="admin_suite_settings"),
    path("settings/edit/", admin_views.admin_suite_settings_edit, name="admin_suite_settings_edit"),
    path("settings/email/", admin_views.admin_suite_email_settings, name="admin_suite_email_settings"),
]
