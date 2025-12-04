
from django.contrib import admin

from .models import Tag, TagsSettings
from .models_keyword import KeywordProvider, KeywordSuggestion


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "usage_count", "is_active", "is_curated", "ai_suggested", "merge_into")
    list_filter = ("is_active", "is_curated", "ai_suggested")
    search_fields = ("name", "slug", "normalized_name", "synonyms_text")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("usage_count", "co_occurrence", "last_suggested_at")
    fieldsets = (
        (None, {"fields": ("name", "normalized_name", "slug", "description")}),
        ("Classification", {"fields": ("is_active", "is_curated", "ai_suggested", "importance")}),
        ("Synonyms", {"fields": ("synonyms_text", "synonyms")}),
        ("Merge / Governance", {"fields": ("parent", "path_cache", "merge_into", "deleted_at", "deleted_by")}),
        ("AI Meta", {"fields": ("ai_score", "content_hash", "last_suggested_at", "suggestions")}),
        ("Analytics", {"fields": ("usage_count", "co_occurrence")}),
    )


@admin.register(KeywordProvider)
class KeywordProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "is_enabled", "last_run_at", "last_status")
    list_filter = ("is_enabled", "source")
    search_fields = ("name", "source")
    readonly_fields = ("last_run_at", "last_status")


@admin.register(KeywordSuggestion)
class KeywordSuggestionAdmin(admin.ModelAdmin):
    list_display = ("keyword", "provider", "score", "locale", "category", "created_at")
    search_fields = ("keyword", "normalized", "provider__name")
    list_filter = ("provider", "locale", "category")


# Singleton settings for the Tags app
try:
    from solo.admin import SingletonModelAdmin

    @admin.register(TagsSettings)
    class TagsSettingsAdmin(SingletonModelAdmin):
        list_display = ("allow_public_suggestions", "enable_ai_suggestions", "show_tag_usage")
        fieldsets = (
            ("Tag suggestions", {"fields": ("allow_public_suggestions", "enable_ai_suggestions")}),
            ("Display", {"fields": ("show_tag_usage",)}),
        )

        def has_add_permission(self, request):
            return False
except Exception:
    # If solo is not installed, skip registration to keep app pluggable.
    pass


