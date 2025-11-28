from django.contrib import admin

from .models import (
    AdPlacement,
    AdCreative,
    Campaign,
    PlacementAssignment,
    AffiliateSource,
    AffiliateLink,
    AdEvent,
)


@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "context", "is_active", "locked", "updated_at")
    list_filter = ("is_active", "locked", "context")
    search_fields = ("name", "slug", "code", "context", "page_context")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "is_active", "priority", "weight", "start_at", "end_at")
    list_filter = ("type", "is_active", "ad_network")
    search_fields = ("name",)


@admin.register(AdCreative)
class AdCreativeAdmin(admin.ModelAdmin):
    list_display = ("name", "campaign", "creative_type", "is_active", "locked", "weight")
    list_filter = ("creative_type", "is_active", "locked", "campaign")
    search_fields = ("name", "campaign__name")


@admin.register(PlacementAssignment)
class PlacementAssignmentAdmin(admin.ModelAdmin):
    list_display = ("placement", "creative", "weight", "is_active", "locked")
    list_filter = ("placement", "creative", "is_active", "locked")


@admin.register(AffiliateSource)
class AffiliateSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "network", "base_url", "is_enabled", "locked", "updated_at")
    list_filter = ("network", "is_enabled", "locked")
    search_fields = ("name", "network", "base_url")


@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "affiliate_url", "is_active", "locked", "usage_count")
    list_filter = ("source", "is_active", "locked")
    search_fields = ("name", "affiliate_url", "target_url", "source__name")


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
