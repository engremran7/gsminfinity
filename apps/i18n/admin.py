
from django.contrib import admin

from apps.i18n.models import (
    AppManifest,
    AuditLog,
    FontRegistry,
    LanguageProfile,
    Locale,
    MissingKeyLog,
    Theme,
    ThemeAssignment,
    TranslationKey,
    TranslationValue,
)


@admin.register(Locale)
class LocaleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "direction", "enabled_global")
    list_filter = ("direction", "enabled_global")
    search_fields = ("code", "name")


@admin.register(LanguageProfile)
class LanguageProfileAdmin(admin.ModelAdmin):
    list_display = ("app_id", "site_id", "default_locale", "fallback_locale")
    search_fields = ("app_id", "site_id")


class TranslationValueInline(admin.TabularInline):
    model = TranslationValue
    extra = 0


@admin.register(TranslationKey)
class TranslationKeyAdmin(admin.ModelAdmin):
    list_display = ("app_id", "namespace", "key", "workflow_state", "version", "updated_at")
    list_filter = ("workflow_state", "namespace")
    search_fields = ("app_id", "namespace", "key")
    inlines = [TranslationValueInline]


@admin.register(MissingKeyLog)
class MissingKeyLogAdmin(admin.ModelAdmin):
    list_display = ("app_id", "locale", "key", "route", "created_at")
    list_filter = ("locale", "app_id")
    search_fields = ("key", "route", "app_id")
    readonly_fields = ("app_id", "site_id", "locale", "key", "route", "user_id", "created_at")


@admin.register(FontRegistry)
class FontRegistryAdmin(admin.ModelAdmin):
    list_display = ("code", "family", "font_display")
    search_fields = ("code", "family")


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "mode", "app_id", "site_id", "inherits_from", "is_locked")
    list_filter = ("mode", "is_locked")
    search_fields = ("name", "app_id", "site_id")


@admin.register(ThemeAssignment)
class ThemeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("theme", "app_id", "scope", "route", "user_id", "device_pref", "system_pref")
    list_filter = ("scope",)
    search_fields = ("app_id", "route", "user_id")


@admin.register(AppManifest)
class AppManifestAdmin(admin.ModelAdmin):
    list_display = ("app_id", "default_locale", "version", "updated_at")
    search_fields = ("app_id",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "app_id", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("app_id", "actor__username")
    readonly_fields = ("before", "after", "created_at")


