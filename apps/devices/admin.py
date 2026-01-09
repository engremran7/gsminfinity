
from __future__ import annotations


from django.contrib import admin, messages
from solo.admin import SingletonModelAdmin

from apps.devices.models import AppPolicy, Device, DeviceConfig, DeviceEvent


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "display_name",
        "os_fingerprint",
        "is_trusted",
        "is_blocked",
        "risk_score",
        "last_seen_at",
        "related_users_count",
    )
    list_filter = ("is_trusted", "is_blocked", "risk_score", "last_seen_at")
    search_fields = ("os_fingerprint", "user__email", "user__username", "display_name")
    readonly_fields = ("first_seen_at", "last_seen_at", "related_users_list")

    actions = ["mark_trusted", "block_devices", "unblock_devices", "remove_devices"]

    def related_users_count(self, obj):
        """Count other users on the same OS fingerprint."""
        if not obj.os_fingerprint:
            return 0
        return Device.objects.filter(os_fingerprint=obj.os_fingerprint).values("user").distinct().count()
    related_users_count.short_description = "Users on Device"

    def related_users_list(self, obj):
        """List other users sharing this device fingerprint."""
        if not obj.os_fingerprint:
            return "N/A"
        users = Device.objects.filter(os_fingerprint=obj.os_fingerprint).values_list("user__email", flat=True).distinct()
        return ", ".join(users)
    related_users_list.short_description = "Users sharing this device"

    @admin.action(description="Mark selected devices as trusted")
    def mark_trusted(self, request, queryset):
        updated = queryset.update(is_trusted=True, is_blocked=False)
        self.message_user(request, f"{updated} device(s) marked as trusted.", messages.SUCCESS)

    @admin.action(description="Block selected devices")
    def block_devices(self, request, queryset):
        updated = queryset.update(is_blocked=True, is_trusted=False, max_privilege_level="blocked")
        self.message_user(request, f"{updated} device(s) blocked.", messages.SUCCESS)

    @admin.action(description="Unblock selected devices")
    def unblock_devices(self, request, queryset):
        updated = queryset.update(is_blocked=False, max_privilege_level="normal")
        self.message_user(request, f"{updated} device(s) unblocked.", messages.SUCCESS)

    @admin.action(description="Remove selected devices")
    def remove_devices(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} device(s) removed.", messages.SUCCESS)


@admin.register(DeviceConfig)
class DeviceConfigAdmin(SingletonModelAdmin):
    fieldsets = (
        ("Fingerprinting", {"fields": ("basic_fingerprinting_enabled", "enhanced_fingerprinting_enabled", "allow_server_fallback")}),
        ("Management", {"fields": ("enterprise_device_management_enabled", "max_devices_default", "monthly_device_quota", "yearly_device_quota", "ad_unlock_enabled", "device_expiry_days")}),
        ("Login", {"fields": ("strict_new_device_login", "require_mfa_on_new_device")}),
        ("AI", {"fields": ("ai_risk_scoring_enabled",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Only superusers can change global device config
        return request.user.is_superuser


@admin.register(AppPolicy)
class AppPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "device_locking_mode", "mfa_requirement", "enhanced_fingerprinting", "ai_risk_scoring", "monthly_device_quota", "yearly_device_quota", "ad_unlock_enabled")
    search_fields = ("name",)
    formfield_overrides = {
        AppPolicy._meta.get_field("service_level_rules").__class__: {"widget": admin.widgets.AdminTextareaWidget}
    }

    def has_change_permission(self, request, obj=None):
        # Only superusers can change app policies
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser


@admin.register(DeviceEvent)
class DeviceEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "user", "device", "success", "reason", "ip")
    list_filter = ("event_type", "success", "created_at")
    search_fields = ("user__email", "user__username", "device__os_fingerprint", "reason", "ip", "user_agent")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False


