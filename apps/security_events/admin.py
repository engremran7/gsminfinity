from django.contrib import admin

from .models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("type", "user", "device", "ip", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("type", "ip", "metadata")
    readonly_fields = ("created_at",)
