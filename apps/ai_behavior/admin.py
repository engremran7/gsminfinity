
from django.contrib import admin

from apps.ai_behavior.models import BehaviorInsight


@admin.register(BehaviorInsight)
class BehaviorInsightAdmin(admin.ModelAdmin):
    list_display = ("created_at", "severity", "status", "related_user", "device_identifier", "related_ip")
    list_filter = ("severity", "status", "created_at")
    search_fields = ("device_identifier", "related_ip", "recommendation", "related_user__username", "related_user__email")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


