
from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import (
    LinkableEntity,
    LinkSuggestion,
    Metadata,
    Redirect,
    SchemaEntry,
    SEOModel,
    SEOSettings,
    SitemapEntry,
)


@admin.register(SEOModel)
class SEOModelAdmin(admin.ModelAdmin):
    list_display = ("content_type", "object_id", "locked", "ai_generated", "updated_at")
    list_filter = ("locked", "ai_generated")


@admin.register(Metadata)
class MetadataAdmin(admin.ModelAdmin):
    list_display = ("seo", "meta_title", "noindex", "nofollow", "updated_at")
    search_fields = ("meta_title", "meta_description", "focus_keywords")


@admin.register(SchemaEntry)
class SchemaEntryAdmin(admin.ModelAdmin):
    list_display = ("seo", "schema_type", "locked", "created_at")
    list_filter = ("schema_type", "locked")


@admin.register(SitemapEntry)
class SitemapEntryAdmin(admin.ModelAdmin):
    list_display = ("url", "is_active", "priority", "lastmod")
    list_filter = ("is_active",)
    search_fields = ("url",)


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("source", "target", "is_permanent", "is_active", "created_at")
    list_filter = ("is_permanent", "is_active")
    search_fields = ("source", "target")


@admin.register(LinkableEntity)
class LinkableEntityAdmin(admin.ModelAdmin):
    list_display = ("title", "entity_type", "url", "is_active", "updated_at")
    list_filter = ("entity_type", "is_active")
    search_fields = ("title", "url", "keywords")


@admin.register(LinkSuggestion)
class LinkSuggestionAdmin(admin.ModelAdmin):
    list_display = ("source", "target", "score", "is_applied", "locked", "is_active", "created_at")
    list_filter = ("is_applied", "locked", "is_active")


@admin.register(SEOSettings)
class SEOSettingsAdmin(SingletonModelAdmin):
    list_display = ("seo_enabled", "auto_meta_enabled", "auto_schema_enabled", "auto_linking_enabled")
    fieldsets = (
        (None, {"fields": ("seo_enabled",)}),
        ("Automation", {"fields": ("auto_meta_enabled", "auto_schema_enabled", "auto_linking_enabled")}),
    )

    def has_add_permission(self, request):
        return False


