from django.contrib import admin

from .models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "usage_count", "is_active", "is_deleted")
    list_filter = ("is_active", "is_deleted")
    search_fields = ("name", "slug", "synonyms")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("usage_count",)
