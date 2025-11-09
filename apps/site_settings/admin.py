from django.contrib import admin
from import_export.admin import ExportMixin
from solo.admin import SingletonModelAdmin
from .models import SiteSettings, VerificationMetaTag, VerificationFile, TenantSiteSettings


# --- Meta Tag Verification ---
@admin.register(VerificationMetaTag)
class VerificationMetaTagAdmin(ExportMixin, admin.ModelAdmin):
    """Admin for managing verification meta tags used in site ownership and SEO."""

    list_display = ("provider", "name_attr", "content_attr", "created_at")
    search_fields = ("provider", "name_attr", "content_attr")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


# --- File-Based Verification ---
@admin.register(VerificationFile)
class VerificationFileAdmin(ExportMixin, admin.ModelAdmin):
    """Admin for managing uploaded verification files (e.g. Google, Bing, etc)."""

    list_display = ("provider", "file", "uploaded_at")
    search_fields = ("provider", "file")
    readonly_fields = ("uploaded_at",)
    ordering = ("-uploaded_at",)


# --- Global Site Settings (Singleton) ---
@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin, ExportMixin, admin.ModelAdmin):
    """Enterprise-grade admin for global site configuration and compliance."""

    list_display = (
        "site_name", "site_header", "site_description",
        "maintenance_mode", "recaptcha_enabled", "recaptcha_mode",
        "recaptcha_score_threshold", "max_devices_per_user",
        "enforce_unique_device", "require_mfa",
        "max_login_attempts", "rate_limit_window_seconds",
    )
    search_fields = ("site_name", "site_header", "site_description")
    readonly_fields = ("favicon",)
    filter_horizontal = ("meta_tags", "verification_files")

    fieldsets = (
        ("🔖 Branding", {
            "fields": (
                "site_name", "site_header", "site_description", "favicon",
                "theme_profile", "primary_color", "secondary_color"
            )
        }),
        ("🌍 Locale", {
            "fields": (
                "default_language", "timezone", "enable_localization"
            )
        }),
        ("🤖 AI Personalization", {
            "fields": (
                "enable_ai_personalization", "ai_theme_mode", "ai_model_version"
            )
        }),
        ("🔐 Security & Features", {
            "fields": (
                "enable_signup", "enable_password_reset",
                "enable_notifications", "maintenance_mode"
            )
        }),
        ("🧠 reCAPTCHA", {
            "fields": (
                "recaptcha_enabled", "recaptcha_mode",
                "recaptcha_public_key", "recaptcha_private_key",
                "recaptcha_score_threshold", "recaptcha_timeout_ms"
            )
        }),
        ("📱 Device & MFA", {
            "fields": (
                "max_devices_per_user", "lock_duration_minutes",
                "fingerprint_mode", "enforce_unique_device",
                "require_mfa", "mfa_totp_issuer"
            )
        }),
        ("📧 Email Verification", {
            "fields": (
                "email_verification_code_length", "email_verification_code_type"
            )
        }),
        ("🛡️ Robustness", {
            "fields": (
                "max_login_attempts", "rate_limit_window_seconds", "cache_ttl_seconds"
            )
        }),
        ("📂 Verification Resources", {
            "fields": ("meta_tags", "verification_files")
        }),
    )


# --- Per-Tenant Site Settings ---
@admin.register(TenantSiteSettings)
class TenantSiteSettingsAdmin(admin.ModelAdmin):
    """Admin for managing per-tenant overrides linked to django.contrib.sites."""

    list_display = ("site", "theme_profile", "primary_color", "secondary_color")
    search_fields = ("site__domain", "theme_profile")
    filter_horizontal = ("meta_tags", "verification_files")
    ordering = ("site",)