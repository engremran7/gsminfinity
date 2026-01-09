from django.contrib import admin

from apps.crawler_guard.models import CrawlerEvent, CrawlerRule


@admin.register(CrawlerRule)
class CrawlerRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "path_pattern",
        "requests_per_minute",
        "action",
        "priority",
        "stop_processing",
        "is_enabled",
    )
    list_filter = ("action", "is_enabled", "stop_processing")
    search_fields = ("name", "path_pattern")
    ordering = ("name",)


@admin.register(CrawlerEvent)
class CrawlerEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "ip", "path", "action_taken", "rule_triggered")
    list_filter = ("action_taken", "rule_triggered", "created_at")
    search_fields = ("ip", "path", "user_agent", "device_identifier")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
