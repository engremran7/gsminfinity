from django.contrib import admin

from apps.app_registry.models import AppEntry


@admin.register(AppEntry)
class AppEntryAdmin(admin.ModelAdmin):
    list_display = ("app_id", "display_name", "min_identity_level", "updated_at")
    search_fields = ("app_id", "display_name", "routes")
    list_filter = ("min_identity_level",)
    readonly_fields = ("created_at", "updated_at")
