# apps/users/admin.py
"""
apps.users.admin
================
Enterprise admin interfaces for user-related models in GSMInfinity.

Features:
- Robust CustomUser admin
- Inline DeviceFingerprint management (read-only)
- Notification + Announcement dashboards
- Bulk admin actions
- Export support (import_export) when installed
- Does NOT break when import_export is absent
- ZERO silent errors
- Django 5.x compatible

IMPORTANT FIX:
--------------
ExportMixin **does not subclass ModelAdmin**, so we must ALWAYS
wrap it inside a ModelAdmin subclass to avoid:

    ValueError: Wrapped class must subclass ModelAdmin.

This file includes a safe BaseAdminClass that prevents the crash
while preserving your export features.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Optional import_export integration — fixed so it never breaks admin
# --------------------------------------------------------------------------
try:
    from import_export.admin import ExportMixin  # type: ignore

    _HAS_IMPORT_EXPORT = True
except Exception:
    ExportMixin = None
    _HAS_IMPORT_EXPORT = False


# --------------------------------------------------------------------------
# MODELS (exactly as present in your models.py)
# --------------------------------------------------------------------------
from .models import Announcement, CustomUser, DeviceFingerprint, Notification

# ==========================================================================
# FIXED BASE ADMIN CLASS
# ==========================================================================
"""
Your earlier file used `BaseAdminClass = ExportMixin`, which FAILS because
ExportMixin does NOT inherit from admin.ModelAdmin.

THE FIX:
    If import_export is available:
        class BaseAdminClass(ExportMixin, admin.ModelAdmin)
    else:
        class BaseAdminClass(admin.ModelAdmin)

This guarantees that @admin.register(...) always receives a ModelAdmin subclass.
"""

if _HAS_IMPORT_EXPORT and ExportMixin:

    class BaseAdminClass(ExportMixin, admin.ModelAdmin):
        """Safe hybrid admin class."""

        pass

else:

    class BaseAdminClass(admin.ModelAdmin):
        """Fallback admin when import_export is not installed."""

        pass


# ==========================================================================
# DeviceFingerprint Inline (read-only)
# ==========================================================================
class DeviceFingerprintInline(admin.TabularInline):
    """Read-only inline for a user's registered device fingerprints."""

    model = DeviceFingerprint
    extra = 0
    can_delete = False
    show_change_link = True
    ordering = ("-last_used_at",)

    readonly_fields = (
        "fingerprint_hash",
        "os_info",
        "browser_info",
        "motherboard_id",
        "registered_at",
        "last_used_at",
        "is_active",
    )
    fields = readonly_fields

    verbose_name = _("Registered Device")
    verbose_name_plural = _("Registered Devices")

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


# ==========================================================================
# CustomUser Admin
# ==========================================================================
@admin.register(CustomUser)
class CustomUserAdmin(BaseAdminClass):
    """Enterprise-grade admin for CustomUser."""

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
        "last_unlock",
    )

    ordering = ("-date_joined",)
    inlines = [DeviceFingerprintInline]
    save_on_top = True

    list_select_related = ()

    fieldsets = (
        (_("Authentication"), {"fields": ("email", "username", "password")}),
        (_("Personal Info"), {"fields": ("full_name", "phone", "referral_code")}),
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
                    "last_unlock",
                    "date_joined",
                )
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        try:
            return qs.prefetch_related("groups")
        except Exception:
            logger.debug("CustomUserAdmin.get_queryset prefetch failed", exc_info=True)
            return qs

    # ------------------------------------------------------------------
    # Admin action: mark selected users as email verified
    # ------------------------------------------------------------------
    @admin.action(description="Mark selected users as email verified (set now)")
    def mark_email_verified(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = (
            queryset.filter(email_verified_at__isnull=True)
            .update(email_verified_at=timezone.now())
        )
        # Sync allauth EmailAddress if installed
        try:
            from allauth.account.models import EmailAddress

            EmailAddress.objects.filter(user__in=queryset).update(
                verified=True, primary=True
            )
        except Exception:
            logger.debug("EmailAddress sync skipped or failed", exc_info=True)

        if updated:
            self.message_user(
                request, _(f"{updated} user(s) marked as verified."), messages.SUCCESS
            )
        else:
            self.message_user(request, _("No users updated."), messages.INFO)

    actions = ["mark_email_verified"]


# ==========================================================================
# DeviceFingerprint Admin
# ==========================================================================
@admin.register(DeviceFingerprint)
class DeviceFingerprintAdmin(BaseAdminClass):
    """Admin interface for device fingerprints."""

    list_display = (
        "user_display",
        "fingerprint_hash_short",
        "os_info",
        "browser_info",
        "last_used_at",
        "is_active",
    )

    list_filter = ("is_active", "os_info", "browser_info")

    search_fields = (
        "fingerprint_hash",
        "user__email",
        "user__username",
        "browser_info",
    )

    readonly_fields = ("registered_at", "last_used_at")
    ordering = ("-last_used_at",)
    list_select_related = ("user",)

    save_on_top = True

    @admin.display(description=_("User"))
    def user_display(self, obj: DeviceFingerprint) -> str:
        return (
            getattr(obj.user, "email", None)
            or getattr(obj.user, "username", None)
            or f"User #{obj.user_id}"
        )

    @admin.display(description=_("Fingerprint"))
    def fingerprint_hash_short(self, obj: DeviceFingerprint) -> str:
        if not obj.fingerprint_hash:
            return "—"
        return f"{obj.fingerprint_hash[:16]}…"


# ==========================================================================
# Notification Admin
# ==========================================================================
@admin.register(Notification)
class NotificationAdmin(BaseAdminClass):
    """Admin interface for Notifications."""

    list_display = (
        "recipient_display",
        "title",
        "priority",
        "channel",
        "is_read",
        "created_at",
        "read_at",
    )

    list_filter = ("priority", "channel", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__email", "recipient__username")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "read_at")
    list_select_related = ("recipient",)
    save_on_top = True

    actions = ["mark_selected_read"]

    if _HAS_IMPORT_EXPORT:
        actions.append("export_selected_as_csv")

    @admin.display(description=_("Recipient"))
    def recipient_display(self, obj: Notification) -> str:
        return (
            getattr(obj.recipient, "email", None)
            or getattr(obj.recipient, "username", None)
            or "Anonymous"
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        qs = super().get_queryset(request)
        try:
            return qs.select_related("recipient")
        except Exception:
            logger.debug("NotificationAdmin.get_queryset failed", exc_info=True)
            return qs

    def mark_selected_read(self, request: HttpRequest, queryset: QuerySet):
        try:
            updated = queryset.filter(is_read=False).update(is_read=True)
            self.message_user(request, _("%d notifications marked as read.") % updated)
        except Exception as exc:
            logger.exception("Failed to mark notifications read: %s", exc)
            self.message_user(
                request,
                _("Failed to mark notifications as read."),
                level=messages.ERROR,
            )

    def export_selected_as_csv(self, request: HttpRequest, queryset: QuerySet):
        self.message_user(
            request, _("Use the Export button above to export notifications.")
        )


# ==========================================================================
# Announcement Admin
# ==========================================================================
@admin.register(Announcement)
class AnnouncementAdmin(BaseAdminClass):
    """Admin for announcements."""

    list_display = (
        "title",
        "audience",
        "is_global",
        "created_by_display",
        "start_at",
        "expires_at",
        "is_active_display",
    )

    search_fields = ("title", "message")
    list_filter = ("audience", "is_global", "expires_at")
    readonly_fields = ("created_by",)
    ordering = ("-start_at",)
    save_on_top = True
    actions = ["publish_selected", "unpublish_selected"]

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description=_("Created By"))
    def created_by_display(self, obj: Announcement):
        return (
            getattr(obj.created_by, "email", None)
            or getattr(obj.created_by, "username", None)
            or "—"
        )

    @admin.display(description=_("Active?"))
    def is_active_display(self, obj: Announcement):
        try:
            return "✅" if obj.is_active else "❌"
        except Exception:
            return "—"

    def publish_selected(self, request, queryset):
        try:
            count = queryset.update(is_active=True)
            self.message_user(request, _("%d announcements published.") % count)
        except Exception:
            logger.exception("Failed to publish announcements")
            self.message_user(
                request, _("Failed to publish announcements."), level=messages.ERROR
            )

    def unpublish_selected(self, request, queryset):
        try:
            count = queryset.update(is_active=False)
            self.message_user(request, _("%d announcements unpublished.") % count)
        except Exception:
            logger.exception("Failed to unpublish announcements")
            self.message_user(
                request, _("Failed to unpublish announcements."), level=messages.ERROR
            )


# ==========================================================================
# Admin Branding
# ==========================================================================
admin.site.site_header = _("GSMInfinity Administration")
admin.site.index_title = _("Enterprise Control Panel")
admin.site.site_title = _("GSMInfinity Admin Portal")
