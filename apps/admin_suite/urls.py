from django.urls import path, re_path
from django.views.generic import RedirectView

from apps.admin_suite import views as admin_views
from apps.admin_suite import (
    views_distribution,
    views_extended,
    views_infrastructure,
    views_users,
)

app_name = "admin_suite"

urlpatterns = [
    # Redirect legacy/popup links for Category to Admin Suite Categories
    re_path(
        r"^blog/category/.*$",
        RedirectView.as_view(
            pattern_name="admin_suite:blog_categories", query_string=True
        ),
    ),
    # Authentication
    path("login/", admin_views.AdminSuiteLoginView.as_view(), name="admin_suite_login"),
    path(
        "login/security-question/",
        admin_views.admin_suite_security_question,
        name="admin_suite_security_question",
    ),
    path(
        "login/security-question/setup/",
        admin_views.admin_suite_security_question_setup,
        name="admin_suite_security_question_setup",
    ),
    path(
        "login/security-question/reset/",
        admin_views.admin_suite_password_reset,
        name="admin_suite_password_reset",
    ),
    # Dashboard
    path("", admin_views.admin_suite, name="admin_suite"),
    path("dashboard/", admin_views.admin_suite, name="dashboard"),
    path(
        "command-search/", admin_views.admin_suite_command_search, name="command_search"
    ),
    # Security Management
    path("security/", admin_views.admin_suite_security, name="security"),
    path("security/devices/", admin_views.admin_suite_security_devices, name="devices"),
    path(
        "security/crawlers/", admin_views.admin_suite_security_crawlers, name="crawlers"
    ),
    path("security/risk/", admin_views.admin_suite_security_risk, name="risk_insights"),
    path(
        "security/events/",
        admin_views.admin_suite_security_events,
        name="security_events",
    ),
    # User Administration
    path("users/", admin_views.admin_suite_users, name="users"),
    path(
        "users/sessions/", admin_views.admin_suite_user_sessions, name="user_sessions"
    ),
    path("users/staff/", admin_views.admin_suite_staff_users, name="staff_users"),
    path(
        "users/social-providers/",
        views_users.admin_suite_social_providers,
        name="social_providers",
    ),
    path(
        "users/social-providers/<str:provider_id>/",
        views_users.admin_suite_social_provider_detail,
        name="social_provider_detail",
    ),
    path(
        "users/<str:user_id>/", admin_views.admin_suite_user_detail, name="user_detail"
    ),
    # Content Operations
    path("pages/", admin_views.admin_suite_pages, name="pages"),
    path("blog/", admin_views.admin_suite_blog, name="blog"),
    path(
        "blog/categories/",
        admin_views.admin_suite_blog_categories,
        name="blog_categories",
    ),
    path("content/", admin_views.admin_suite_content, name="content"),
    path(
        "content/pending/",
        admin_views.admin_suite_pending_approval,
        name="pending_approval",
    ),
    path("comments/", admin_views.admin_suite_comments, name="comments"),
    path("seo/", admin_views.admin_suite_seo, name="seo"),
    path("tags/", admin_views.admin_suite_tags, name="tags"),
    # Marketing & Growth
    path("marketing/", admin_views.admin_suite_marketing, name="marketing"),
    path("ads/", admin_views.admin_suite_ads, name="ads"),
    path(
        "ads/campaigns/",
        views_infrastructure.admin_suite_ads_campaigns,
        name="ads_campaigns",
    ),
    path(
        "ads/placements/",
        views_infrastructure.admin_suite_ads_placements,
        name="ads_placements",
    ),
    path(
        "ads/creatives/",
        views_infrastructure.admin_suite_ads_creatives,
        name="ads_creatives",
    ),
    path(
        "ads/analytics/",
        views_infrastructure.admin_suite_ads_analytics,
        name="ads_analytics",
    ),
    path("distribution/", admin_views.admin_suite_distribution, name="distribution"),
    path(
        "distribution/social-posting/",
        views_distribution.admin_suite_social_posting,
        name="social_posting",
    ),
    path(
        "distribution/social-posting/<str:account_id>/",
        views_distribution.admin_suite_social_posting_detail,
        name="social_posting_detail",
    ),
    path(
        "distribution/social-posting/oauth/callback/<str:platform>/",
        views_distribution.admin_suite_social_posting_oauth_callback,
        name="social_posting_oauth_callback",
    ),
    # Storage Management
    path("storage/", views_infrastructure.admin_suite_storage, name="storage"),
    path(
        "storage/files/",
        views_infrastructure.admin_suite_storage_files,
        name="storage_files",
    ),
    path(
        "storage/providers/",
        views_infrastructure.admin_suite_storage_providers,
        name="storage_providers",
    ),
    path(
        "storage/providers/<str:provider_id>/",
        views_infrastructure.admin_suite_storage_provider_detail,
        name="storage_provider_detail",
    ),
    # Firmwares Management
    path("firmwares/", views_infrastructure.admin_suite_firmwares, name="firmwares"),
    path(
        "firmwares/brands/",
        views_infrastructure.admin_suite_firmwares_brands,
        name="firmwares_brands",
    ),
    path(
        "firmwares/models/",
        views_infrastructure.admin_suite_firmwares_models,
        name="firmwares_models",
    ),
    # System Configuration
    path("settings/", admin_views.admin_suite_settings, name="settings"),
    path("settings/edit/", admin_views.admin_suite_settings_edit, name="settings_edit"),
    path(
        "settings/email/", admin_views.admin_suite_email_settings, name="email_settings"
    ),
    path("settings/ai/", admin_views.admin_suite_ai, name="ai_settings"),
    path("consent/", admin_views.admin_suite_consent, name="consent"),
    path("registry/", admin_views.admin_suite_registry, name="app_registry"),
    # i18n / Localization (NEW)
    path("i18n/", views_extended.admin_suite_i18n, name="i18n"),
    path(
        "i18n/translations/",
        views_extended.admin_suite_i18n_translations,
        name="i18n_translations",
    ),
    # Device Settings (Extended)
    path(
        "devices/settings/",
        views_extended.admin_suite_devices_settings,
        name="devices_settings",
    ),
    # AI Extended Management
    path("ai/endpoints/", views_extended.admin_suite_ai_endpoints, name="ai_endpoints"),
    path("ai/knowledge/", views_extended.admin_suite_ai_knowledge, name="ai_knowledge"),
    path("ai/workflows/", views_extended.admin_suite_ai_workflows, name="ai_workflows"),
    # Feature Toggles
    path("features/", views_extended.admin_suite_features, name="features"),
    # Blog Posts (Extended)
    path("blog/posts/", views_extended.admin_suite_blog_posts, name="blog_posts"),
    # Crawler Guard
    path(
        "security/crawler-rules/",
        views_extended.admin_suite_crawler_rules,
        name="crawler_rules",
    ),
    # Legacy URL aliases (backward compatibility)
    path("ai/", admin_views.admin_suite_ai, name="admin_suite_ai"),
    path(
        "security/devices-legacy/",
        admin_views.admin_suite_security_devices,
        name="admin_suite_security_devices",
    ),
    path(
        "security/crawlers-legacy/",
        admin_views.admin_suite_security_crawlers,
        name="admin_suite_security_crawlers",
    ),
    path(
        "security/risk-legacy/",
        admin_views.admin_suite_security_risk,
        name="admin_suite_security_risk",
    ),
    path(
        "consent-legacy/", admin_views.admin_suite_consent, name="admin_suite_consent"
    ),
    path("pages-legacy/", admin_views.admin_suite_pages, name="admin_suite_pages"),
    path("blog-legacy/", admin_views.admin_suite_blog, name="admin_suite_blog"),
    path(
        "blog/categories-legacy/",
        admin_views.admin_suite_blog_categories,
        name="admin_suite_blog_categories",
    ),
    path(
        "content-legacy/", admin_views.admin_suite_content, name="admin_suite_content"
    ),
    path(
        "marketing-legacy/",
        admin_views.admin_suite_marketing,
        name="admin_suite_marketing",
    ),
    path(
        "distribution-legacy/",
        admin_views.admin_suite_distribution,
        name="admin_suite_distribution",
    ),
    path("ads-legacy/", admin_views.admin_suite_ads, name="admin_suite_ads"),
    path("tags-legacy/", admin_views.admin_suite_tags, name="admin_suite_tags"),
    path("seo-legacy/", admin_views.admin_suite_seo, name="admin_suite_seo"),
    path(
        "registry-legacy/",
        admin_views.admin_suite_registry,
        name="admin_suite_registry",
    ),
    path(
        "comments-legacy/",
        admin_views.admin_suite_comments,
        name="admin_suite_comments",
    ),
    path("users-legacy/", admin_views.admin_suite_users, name="admin_suite_users"),
    path(
        "users-legacy/<str:user_id>/",
        admin_views.admin_suite_user_detail,
        name="admin_suite_user_detail",
    ),
    path(
        "settings-legacy/",
        admin_views.admin_suite_settings,
        name="admin_suite_settings",
    ),
    path(
        "settings/edit-legacy/",
        admin_views.admin_suite_settings_edit,
        name="admin_suite_settings_edit",
    ),
    path(
        "settings/email-legacy/",
        admin_views.admin_suite_email_settings,
        name="admin_suite_email_settings",
    ),
]
