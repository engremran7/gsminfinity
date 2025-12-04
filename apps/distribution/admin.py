
from __future__ import annotations

from django.contrib import admin
from django import forms
from django.db import models

from .models import (
    SocialAccount,
    ShareTemplate,
    ContentVariant,
    SharePlan,
    ShareJob,
    ShareLog,
    WebSubSubscription,
    SyndicationPartner,
    DistributionSettings,
)


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("channel", "account_name", "is_active", "last_tested_at")
    list_filter = ("channel", "is_active")
    search_fields = ("account_name",)
    formfield_overrides = {
        # Avoid rendering tokens in plain text in admin forms.
        # PasswordInput with render_value=True keeps existing tokens hidden but preserved.
        models.TextField: {"widget": forms.PasswordInput(render_value=True)},
    }


@admin.register(ShareTemplate)
class ShareTemplateAdmin(admin.ModelAdmin):
    list_display = ("channel", "name", "is_default")
    list_filter = ("channel", "is_default")
    search_fields = ("name",)


@admin.register(ContentVariant)
class ContentVariantAdmin(admin.ModelAdmin):
    list_display = ("post", "channel", "variant_type", "generated_at")
    list_filter = ("channel", "variant_type")
    search_fields = ("post__title",)


@admin.register(SharePlan)
class SharePlanAdmin(admin.ModelAdmin):
    list_display = ("post", "status", "schedule_at", "created_at")
    list_filter = ("status",)
    search_fields = ("post__title",)


@admin.register(ShareJob)
class ShareJobAdmin(admin.ModelAdmin):
    list_display = ("post", "channel", "status", "schedule_at", "attempt_count")
    list_filter = ("channel", "status")
    search_fields = ("post__title", "external_post_id")


@admin.register(ShareLog)
class ShareLogAdmin(admin.ModelAdmin):
    list_display = ("job", "level", "created_at")
    list_filter = ("level",)
    search_fields = ("message",)


@admin.register(WebSubSubscription)
class WebSubSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("topic_url", "hub_url", "active", "last_pinged_at")
    list_filter = ("active",)


@admin.register(SyndicationPartner)
class SyndicationPartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "format", "enabled")
    list_filter = ("enabled", "format")
    search_fields = ("name",)


try:
    from solo.admin import SingletonModelAdmin

    @admin.register(DistributionSettings)
    class DistributionSettingsAdmin(SingletonModelAdmin):
        list_display = ("distribution_enabled",)
        fieldsets = ((None, {"fields": ("distribution_enabled",)}),)

        def has_add_permission(self, request):
            return False
except Exception:
    pass


