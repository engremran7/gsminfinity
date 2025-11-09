"""
apps.users.admin
----------------
Enterprise admin interfaces for user-related models in GSMInfinity.

✅ Includes:
- CustomUser admin (searchable, exportable)
- DeviceFingerprint admin (per-user device management)
- Notification & Announcement admin panels
- Inline improvements and safe read-only fields
- Compatible with Django 5.x, import_export, and custom user model
"""

from django.contrib import admin
from import_export.admin import ExportMixin
from django.utils.translation import gettext_lazy as _

from .models import (
    CustomUser,
    DeviceFingerprint,
    Notification,
    Announcement,
)


# ======================================================================
#  Inline Components
# ======================================================================


class DeviceFingerprintInline(admin.TabularInline):
    """
    Inline display of DeviceFingerprints within the user admin detail page.
    """
    model = DeviceFingerprint
    extra = 0
    readonly_fields = (
        "fingerprint_hash",
        "os_info",
        "browser_info",
        "motherboard_id",
        "registered_at",
        "last_used_at",
        "is_active",
    )
    can_delete = False
    ordering = ("-last_used_at",)
    verbose_name = _("Registered Device")
    verbose_name_plural = _("Registered Devices")


# ======================================================================
#  CustomUser Admin
# ======================================================================


@admin.register(CustomUser)
class CustomUserAdmin(ExportMixin, admin.ModelAdmin):
    """
    Admin configuration for CustomUser model.
    """
    list_display = (
        "email",
        "username",
        "full_name",
        "is_active",
        "is_staff",
        "is_superuser",
        "credits",
        "signup_method",
        "date_joined",
    )
    search_fields = (
        "email",
        "username",
        "full_name",
        "phone",
        "referral_code",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "signup_method",
    )
    readonly_fields = (
        "referral_code",
        "date_joined",
        "email_verified_at",
        "last_unlock",
    )
    inlines = [DeviceFingerprintInline]
    ordering = ("-date_joined",)
    fieldsets = (
        (_("Authentication"), {"fields": ("email", "username", "password")}),
        (
            _("Personal Info"),
            {"fields": ("full_name", "phone", "referral_code")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Additional Info"),
            {
                "fields": (
                    "credits",
                    "signup_method",
                    "email_verified_at",
                    "last_unlock",
                    "date_joined",
                )
            },
        ),
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


# ======================================================================
#  DeviceFingerprint Admin
# ======================================================================


@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(ExportMixin, admin.ModelAdmin):
    """
    Manages all registered device fingerprints.
    """
    list_display = (
        "user",
        "fingerprint_hash",
        "os_info",
        "browser_info",
        "motherboard_id",
        "last_used_at",
        "is_active",
    )
    list_filter = ("is_active", "os_info")
    search_fields = (
        "fingerprint_hash",
        "user__email",
        "user__username",
        "browser_info",
    )
    readonly_fields = (
        "registered_at",
        "last_used_at",
    )
    ordering = ("-last_used_at",)
    list_select_related = ("user",)

    class Meta:
        verbose_name = _("Device Fingerprint")
        verbose_name_plural = _("Device Fingerprints")


# ======================================================================
#  Notification Admin
# ======================================================================


@admin.register(Notification)
class NotificationAdmin(ExportMixin, admin.ModelAdmin):
    """
    Enterprise-grade notification log for users.
    """
    list_display = (
        "recipient",
        "title",
        "priority",
        "channel",
        "created_at",
        "is_read",
        "read_at",
    )
    list_filter = (
        "priority",
        "channel",
        "is_read",
        "created_at",
    )
    search_fields = (
        "title",
        "message",
        "recipient__email",
        "recipient__username",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "read_at")

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")


# ======================================================================
#  Announcement Admin
# ======================================================================


@admin.register(Announcement)
class AnnouncementAdmin(ExportMixin, admin.ModelAdmin):
    """
    Enterprise announcements / global messages.
    """
    list_display = (
        "title",
        "audience",
        "is_global",
        "created_by",
        "start_at",
        "expires_at",
    )
    list_filter = (
        "audience",
        "is_global",
        "expires_at",
    )
    search_fields = (
        "title",
        "message",
    )
    readonly_fields = ("created_by",)
    ordering = ("-start_at",)

    def save_model(self, request, obj, form, change):
        """Auto-assign creator on first save."""
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    class Meta:
        verbose_name = _("Announcement")
        verbose_name_plural = _("Announcements")


# ======================================================================
#  Admin Branding
# ======================================================================

admin.site.site_header = _("GSM Infinity Admin")
admin.site.index_title = _("Enterprise Management")
admin.site.site_title = _("Admin Portal")
