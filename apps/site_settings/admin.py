from __future__ import annotations

import logging

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportMixin
from solo.admin import SingletonModelAdmin

from .models import SiteSettings, VerificationFile, VerificationMetaTag

logger = logging.getLogger(__name__)


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


def _preview(obj, field_name: str, height: int = 60):
    try:
        field = getattr(obj, field_name, None)
        if not field or not getattr(field, "url", None):
            return "-"
        return format_html(
            '<img src="{}" style="height:{}px; border-radius:6px;" />',
            field.url,
            height,
        )
    except Exception:
        return "-"


@admin.register(SiteSettings)
class SiteSettingsAdmin(ExportMixin, SingletonModelAdmin):
    list_display = (
        "site_name",
        "maintenance_mode",
        "force_https",
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

    fieldsets = (
        (
            "Branding & Theme",
            {
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
                    "primary_color",
                    "secondary_color",
                ),
                "description": "Core branding only. Runtime themes/colors come from the Themes app.",
            },
        ),
        (
            "Locale & Internationalization",
            {
                "fields": (
                    "default_language",
                    "timezone",
                    "enable_localization",
                    "featured_languages",
                ),
                "description": "Featured languages appear in the header dropdown (max 10). Use comma-separated codes like: en,ar,fr,de,es",
            },
        ),
        (
            "Ops & Availability",
            {
                "fields": (
                    "maintenance_mode",
                    "force_https",
                ),
                "description": "App-specific toggles now live in each app's settings and AppRegistry.",
            },
        ),
        (
            "Email (Gmail SMTP)",
            {
                "fields": (
                    "gmail_enabled",
                    "gmail_username",
                    "gmail_app_password",
                    "gmail_from_email",
                ),
                "description": "Configure Gmail with an app password. From defaults to the Gmail username when blank.",
            },
        ),
        (
            "reCAPTCHA Configuration",
            {
                "fields": (
                    "recaptcha_enabled",
                    "recaptcha_mode",
                    "recaptcha_public_key",
                    "recaptcha_private_key",
                    "recaptcha_score_threshold",
                    "recaptcha_timeout_ms",
                ),
            },
        ),
    )

    inlines = [SiteSettingsMetaTagInline, SiteSettingsFileInline]

    def logo_preview(self, obj):
        return _preview(obj, "logo")

    def dark_logo_preview(self, obj):
        return _preview(obj, "dark_logo")

    def favicon_preview(self, obj):
        return _preview(obj, "favicon")

    logo_preview.short_description = "Logo Preview"
    dark_logo_preview.short_description = "Dark Logo Preview"
    favicon_preview.short_description = "Favicon Preview"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        logger.info(
            "SiteSettings updated by %s (force_https=%s, maintenance_mode=%s)",
            request.user,
            obj.force_https,
            obj.maintenance_mode,
        )

    def has_add_permission(self, request):
        return False


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


admin.site.site_header = _("Administration Portal")
admin.site.index_title = _("Enterprise Settings")
admin.site.site_title = _("Site Configuration")
