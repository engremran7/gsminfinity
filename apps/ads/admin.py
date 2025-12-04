
from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import (
    AdPlacement,
    AdCreative,
    Campaign,
    PlacementAssignment,
    AffiliateSource,
    AffiliateLink,
    AdEvent,
    AdsSettings,
)


@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "context", "is_active", "locked", "updated_at")
    list_filter = ("is_active", "locked", "context")
    search_fields = ("name", "slug", "code", "context", "page_context")
    exclude = ("is_deleted", "deleted_at", "deleted_by")
    readonly_fields = ("created_by", "updated_by")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "is_active", "priority", "weight", "start_at", "end_at")
    list_filter = ("type", "is_active", "ad_network")
    search_fields = ("name",)
    exclude = ("is_deleted", "deleted_at", "deleted_by")
    readonly_fields = ("created_by", "updated_by")


@admin.register(AdCreative)
class AdCreativeAdmin(admin.ModelAdmin):
    list_display = ("name", "campaign", "creative_type", "is_active", "locked", "weight")
    list_filter = ("creative_type", "is_active", "locked", "campaign")
    search_fields = ("name", "campaign__name")
    exclude = ("is_deleted", "deleted_at", "deleted_by")
    readonly_fields = ("created_by", "updated_by")


@admin.register(PlacementAssignment)
class PlacementAssignmentAdmin(admin.ModelAdmin):
    list_display = ("placement", "creative", "weight", "is_active", "locked")
    list_filter = ("placement", "creative", "is_active", "locked")
    exclude = ("is_deleted", "deleted_at", "deleted_by")
    readonly_fields = ("created_by", "updated_by")


@admin.register(AffiliateSource)
class AffiliateSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "network", "base_url", "is_enabled", "locked", "updated_at")
    list_filter = ("network", "is_enabled", "locked")
    search_fields = ("name", "network", "base_url")
    exclude = ("is_deleted", "deleted_at", "deleted_by")
    readonly_fields = ("created_by", "updated_by")


@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "affiliate_url", "is_active", "locked", "usage_count")
    list_filter = ("source", "is_active", "locked")
    search_fields = ("name", "affiliate_url", "target_url", "source__name")
    exclude = ("is_deleted", "deleted_at", "deleted_by")
    readonly_fields = ("created_by", "updated_by")


@admin.register(AdEvent)
class AdEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "campaign", "placement", "creative", "page_url", "created_at")
    list_filter = ("event_type", "campaign")
    readonly_fields = (
        "event_type",
        "campaign",
        "placement",
        "creative",
        "user",
        "request_meta",
        "page_url",
        "referrer_url",
        "user_agent",
        "session_id",
        "created_at",
    )


@admin.register(AdsSettings)
class AdsSettingsAdmin(SingletonModelAdmin):
    list_display = ("ads_enabled", "affiliate_enabled", "ad_networks_enabled", "ad_aggressiveness_level")
    fieldsets = (
        (None, {"fields": ("ads_enabled", "ad_aggressiveness_level")}),
        ("Affiliate / Networks", {"fields": ("affiliate_enabled", "ad_networks_enabled")}),
    )

    def has_add_permission(self, request):
        # Singleton – always edit existing row
        return False


