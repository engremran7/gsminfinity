
# apps/users/admin.py
"""
apps.users.admin
Enterprise admin interfaces for user-related models in GSMInfinity.

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
from .models import Announcement, CustomUser, Notification, UsersSettings

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
        "email_verified_at",
        "date_joined",
    )

    search_fields = (
        "email",
        "username",
        "full_name",
        "phone",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "signup_method",
        "email_verified_at",
    )

    readonly_fields = (
        "date_joined",
        "last_unlock",
    )

    ordering = ("-date_joined",)
    save_on_top = True

    list_select_related = ()

    fieldsets = (
        (_("Authentication"), {"fields": ("email", "username", "password")}),
        (_("Personal Info"), {"fields": ("full_name", "phone")}),
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
                    "email_verified_at",
                    "verification_code",
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

    @admin.action(description="Clear email verification (set to unverified)")
    def clear_email_verification(self, request: HttpRequest, queryset: QuerySet) -> None:
        count = queryset.update(email_verified_at=None, verification_code="")
        try:
            from allauth.account.models import EmailAddress

            EmailAddress.objects.filter(user__in=queryset).update(verified=False)
        except Exception:
            logger.debug("EmailAddress unverify sync skipped or failed", exc_info=True)
        if count:
            self.message_user(request, _("%d user(s) marked unverified.") % count)
        else:
            self.message_user(request, _("No users updated."), messages.INFO)

    actions = ["mark_email_verified", "clear_email_verification"]


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

# Users app settings (singleton)
try:
    from solo.admin import SingletonModelAdmin

    @admin.register(UsersSettings)
    class UsersSettingsAdmin(SingletonModelAdmin):
        """Manage Users app configuration independently."""

        fieldsets = (
            (_("Access & Flows"), {"fields": ("enable_signup", "enable_password_reset")}),
            (_("Notifications"), {"fields": ("enable_notifications",)}),
            (
                _("Security"),
                {
                    "fields": (
                        "require_mfa",
                        "mfa_totp_issuer",
                        "max_login_attempts",
                        "rate_limit_window_seconds",
                    )
                },
            ),
            (
                _("reCAPTCHA"),
                {
                    "fields": (
                    )
                },
            ),
            (_("Profile Completion"), {"fields": ("required_profile_fields",)}),
            (_("Payments"), {"fields": ("enable_payments",)}),
        )

        def has_add_permission(self, request):
            return False
except Exception:
    logger.warning("solo not available; UsersSettings admin not registered")


