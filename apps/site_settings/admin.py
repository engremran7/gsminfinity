"""
apps.site_settings.admin
========================
Enterprise Admin Configuration for Site + Tenant Settings.

✔ Django 5.2 / Python 3.12
✔ Supports new branding fields (logo, dark_logo, favicon)
✔ Secure, clean fieldsets (no direct M2M inside)
✔ Through-model inlines for meta-tags & verification files
✔ Image previews inside admin
"""

from __future__ import annotations

import logging
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportMixin
from solo.admin import SingletonModelAdmin

from .models import (
    SiteSettings,
    TenantSiteSettings,
    VerificationMetaTag,
    VerificationFile,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
#  INLINE THROUGH-MODELS
# ------------------------------------------------------------
class SiteSettingsMetaTagInline(admin.TabularInline):
    model = SiteSettings.meta_tags.through
    extra = 0
    verbose_name = _("Verification Meta Tag Link")
    verbose_name_plural = _("Verification Meta Tag Links")


class SiteSettingsFileInline(admin.TabularInline):
    model = SiteSettings.verification_files.through
    extra = 0
    verbose_name = _("Verification File Link")
    verbose_name_plural = _("Verification File Links")


# ------------------------------------------------------------
#  IMAGE PREVIEW HELPERS
# ------------------------------------------------------------
def _preview(obj, field_name: str, height: int = 60):
    """Safe preview for logo, dark_logo, favicon."""
    try:
        field = getattr(obj, field_name, None)
        if not field:
            return "-"
        if not getattr(field, "url", None):
            return "-"
        return format_html(
            '<img src="{}" style="height:{}px; border-radius:6px;" />',
            field.url,
            height,
        )
    except Exception:
        return "-"


# ------------------------------------------------------------
#  SiteSettings Admin (Singleton)
# ------------------------------------------------------------
@admin.register(SiteSettings)
class SiteSettingsAdmin(ExportMixin, SingletonModelAdmin):

    list_display = (
        "site_name",
        "maintenance_mode",
        "force_https",
        "enable_signup",
        "enable_notifications",
        "require_mfa",
        "recaptcha_enabled",
    )

    search_fields = ("site_name", "site_header", "site_description")
    list_per_page = 25
    save_on_top = True

    readonly_fields = (
        "logo_preview",
        "dark_logo_preview",
        "favicon_preview",
    )

    # ----------------------
    # Fieldsets
    # ----------------------
    fieldsets = (
        ("🔖 Branding & Theme", {
            "fields": (
                "site_name",
                "site_header",
                "site_description",

                "logo",
                "logo_preview",

                "dark_logo",
                "dark_logo_preview",

                "favicon",
                "favicon_preview",

                "theme_profile",
                "primary_color",
                "secondary_color",
            ),
        }),

        ("🌍 Locale & Internationalization", {
            "fields": (
                "default_language",
                "timezone",
                "enable_localization",
            ),
        }),

        ("🤖 AI Personalization", {
            "fields": (
                "enable_ai_personalization",
                "ai_theme_mode",
                "ai_model_version",
            ),
        }),

        ("🔐 Security & Features", {
            "fields": (
                "enable_signup",
                "enable_password_reset",
                "enable_notifications",
                "maintenance_mode",
                "force_https",
            ),
        }),

        ("🧠 reCAPTCHA Configuration", {
            "fields": (
                "recaptcha_enabled",
                "recaptcha_mode",
                "recaptcha_public_key",
                "recaptcha_private_key",
                "recaptcha_score_threshold",
                "recaptcha_timeout_ms",
            ),
        }),

        ("📱 Device & MFA Policies", {
            "fields": (
                "max_devices_per_user",
                "lock_duration_minutes",
                "fingerprint_mode",
                "enforce_unique_device",
                "require_mfa",
                "mfa_totp_issuer",
            ),
        }),

        ("📧 Email Verification", {
            "fields": (
                "email_verification_code_length",
                "email_verification_code_type",
            ),
        }),

        ("🛡️ Rate Limiting & Robustness", {
            "fields": (
                "max_login_attempts",
                "rate_limit_window_seconds",
                "cache_ttl_seconds",
            ),
        }),
    )

    inlines = [SiteSettingsMetaTagInline, SiteSettingsFileInline]

    # ----------------------
    # Preview fields
    # ----------------------
    def logo_preview(self, obj):
        return _preview(obj, "logo")

    def dark_logo_preview(self, obj):
        return _preview(obj, "dark_logo")

    def favicon_preview(self, obj):
        return _preview(obj, "favicon")

    logo_preview.short_description = "Logo Preview"
    dark_logo_preview.short_description = "Dark Logo Preview"
    favicon_preview.short_description = "Favicon Preview"

    # ----------------------
    # Save Logger
    # ----------------------
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        logger.info(
            "SiteSettings updated by %s (force_https=%s, maintenance_mode=%s)",
            request.user,
            obj.force_https,
            obj.maintenance_mode,
        )


# ------------------------------------------------------------
#  TENANT SETTINGS ADMIN
# ------------------------------------------------------------
@admin.register(TenantSiteSettings)
class TenantSiteSettingsAdmin(ExportMixin, admin.ModelAdmin):

    list_display = ("site", "theme_profile", "primary_color", "secondary_color")
    search_fields = ("site__domain", "theme_profile")
    ordering = ("site",)
    list_select_related = ("site",)
    list_per_page = 50
    save_on_top = True


# ------------------------------------------------------------
#  VERIFICATION RESOURCES
# ------------------------------------------------------------
@admin.register(VerificationMetaTag)
class VerificationMetaTagAdmin(admin.ModelAdmin):
    list_display = ("provider", "name_attr", "content_attr", "created_at")
    search_fields = ("provider", "name_attr", "content_attr")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    save_on_top = True


@admin.register(VerificationFile)
class VerificationFileAdmin(admin.ModelAdmin):
    list_display = ("provider", "file", "uploaded_at")
    search_fields = ("provider", "file")
    ordering = ("-uploaded_at",)
    readonly_fields = ("uploaded_at",)
    save_on_top = True


# ------------------------------------------------------------
#  Admin Branding (non-project-specific)
# ------------------------------------------------------------
admin.site.site_header = _("Administration Portal")
admin.site.index_title = _("Enterprise Settings")
admin.site.site_title = _("Site Configuration")
