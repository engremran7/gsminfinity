from __future__ import annotations

from django import forms
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils import timezone

from .models import (
    ContentDistribution,
    ContentVariant,
    DistributionSettings,
    ShareJob,
    ShareLog,
    SharePlan,
    ShareTemplate,
    SocialAccount,
    SyndicationPartner,
    WebSubSubscription,
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
    actions = ["mark_tested", "test_connector"]

    @admin.action(description="Mark selected accounts as tested now")
    def mark_tested(self, request, queryset):
        now = timezone.now()
        count = queryset.update(last_tested_at=now)
        self.message_user(request, f"Marked {count} account(s) as tested at {now}.")

    @admin.action(description="Test connector readiness (checks active+access_token)")
    def test_connector(self, request, queryset):
        now = timezone.now()
        ok = 0
        missing = []
        for acc in queryset:
            if acc.is_active and acc.access_token:
                ok += 1
                acc.last_tested_at = now
                acc.save(update_fields=["last_tested_at"])
            else:
                missing.append(f"{acc.channel}:{acc.account_name or acc.pk}")
        msg = f"Tested {ok} account(s)."
        if missing:
            msg += f" Missing token or inactive: {', '.join(missing)}"
        self.message_user(request, msg)


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
    actions = ["retry_jobs", "cancel_jobs", "requeue_jobs"]

    @admin.action(description="Retry selected jobs (set to pending and enqueue)")
    def retry_jobs(self, request, queryset):
        from apps.distribution.tasks import deliver_job

        count = 0
        for job in queryset:
            job.status = "pending"
            job.save(update_fields=["status", "updated_at"])
            deliver_job.delay(job.id)
            count += 1
        self.message_user(request, f"Queued retry for {count} job(s).")

    @admin.action(description="Cancel selected jobs")
    def cancel_jobs(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"Cancelled {updated} job(s).")

    @admin.action(description="Requeue selected jobs (pending)")
    def requeue_jobs(self, request, queryset):
        from apps.distribution.tasks import deliver_job

        count = 0
        for job in queryset:
            job.status = "pending"
            job.save(update_fields=["status", "updated_at"])
            deliver_job.delay(job.id)
            count += 1
        self.message_user(request, f"Requeued {count} job(s).")


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
except ImportError as exc:
    raise ImproperlyConfigured(
        "django-solo is required for DistributionSettings admin"
    ) from exc


@admin.register(DistributionSettings)
class DistributionSettingsAdmin(SingletonModelAdmin):
    """
    Centralized control panel for all distribution automation limits and policies.
    Configure SEO limits, auto-tagging frequency, platform restrictions, and more.
    """

    fieldsets = (
        (
            "🌐 General Distribution Settings",
            {
                "fields": (
                    "distribution_enabled",
                    "auto_fanout_on_publish",
                    "require_admin_approval",
                ),
                "description": (
                    "<strong>Master Controls:</strong> Enable/disable distribution globally, "
                    "auto-publish on post creation, and require manual approval for jobs."
                ),
            },
        ),
        (
            "📱 Platform & Distribution Limits",
            {
                "fields": (
                    "max_platforms_per_content",
                    "distribution_frequency_hours",
                    "default_channels",
                ),
                "description": (
                    "<strong>⚠️ POLICY COMPLIANCE:</strong> Limits prevent spam detection and platform bans. "
                    "<ul>"
                    "<li><strong>Max Platforms:</strong> Recommended 5 or less to avoid spam flags</li>"
                    "<li><strong>Frequency:</strong> Minimum hours between distributions (4-24 recommended)</li>"
                    "<li><strong>Default Channels:</strong> JSON array like ['twitter', 'facebook', 'linkedin']</li>"
                    "</ul>"
                ),
            },
        ),
        (
            "🔍 SEO Limits (Search Engine Guidelines)",
            {
                "fields": (
                    "max_seo_title_length",
                    "max_seo_description_length",
                    "max_seo_tags",
                ),
                "description": (
                    "<strong>Google Best Practices:</strong> "
                    "<ul>"
                    "<li><strong>Title:</strong> Google displays ~60 chars in search results</li>"
                    "<li><strong>Description:</strong> Google displays ~160 chars</li>"
                    "<li><strong>SEO Tags:</strong> 5-10 recommended; more = keyword stuffing penalty</li>"
                    "</ul>"
                ),
            },
        ),
        (
            "🏷️ Auto-Tagging Configuration",
            {
                "fields": ("max_auto_tags", "auto_tag_frequency_days"),
                "description": (
                    "<strong>Content Optimization:</strong> "
                    "<ul>"
                    "<li><strong>Max Auto Tags:</strong> 10-15 recommended; more reduces quality</li>"
                    "<li><strong>Update Frequency:</strong> Days between re-tagging existing content (0 = never)</li>"
                    "</ul>"
                    "<em>Platform limits: Twitter=10 hashtags, Instagram=30, LinkedIn=10</em>"
                ),
            },
        ),
        (
            "🔄 Retry & Error Handling",
            {
                "fields": ("max_retries", "retry_backoff_seconds"),
                "description": (
                    "<strong>Failure Recovery:</strong> "
                    "<ul>"
                    "<li><strong>Max Retries:</strong> Attempts before marking as permanently failed</li>"
                    "<li><strong>Backoff:</strong> Wait time between retries (1800s = 30 min)</li>"
                    "</ul>"
                ),
            },
        ),
        (
            "🚀 Advanced Features",
            {
                "fields": ("allow_indexing_jobs", "enable_firmware_auto_distribution"),
                "description": (
                    "<strong>Optional Features:</strong> "
                    "<ul>"
                    "<li><strong>Indexing:</strong> Auto-submit to Google/Bing (requires API keys)</li>"
                    "<li><strong>Firmware Auto-Distribution:</strong> Auto-publish firmware blog posts</li>"
                    "</ul>"
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return False


@admin.register(ContentDistribution)
class ContentDistributionAdmin(admin.ModelAdmin):
    """
    Tracks individual content distribution jobs across platforms.
    View status, retry failed distributions, and monitor platform delivery.
    """

    list_display = (
        "title",
        "content_type",
        "status",
        "platform_count",
        "distribution_count",
        "created_at",
    )
    list_filter = ("status", "content_type", "created_at")
    search_fields = ("title", "summary")
    readonly_fields = (
        "content_type",
        "object_id",
        "distribution_count",
        "failed_count",
        "created_at",
        "updated_at",
    )
    actions = ["apply_limits_action", "retry_failed"]

    fieldsets = (
        (
            "Content Information",
            {
                "fields": (
                    "content_type",
                    "object_id",
                    "title",
                    "summary",
                    "content_url",
                ),
            },
        ),
        (
            "Distribution Settings",
            {
                "fields": ("target_channels", "status", "priority", "schedule_at"),
            },
        ),
        (
            "Tracking & Metrics",
            {
                "fields": (
                    "distributed_at",
                    "distribution_count",
                    "failed_count",
                    "last_error",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("metadata", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Platforms")
    def platform_count(self, obj):
        return len(obj.target_channels) if obj.target_channels else 0

    @admin.action(description="Apply admin-configured limits to selected")
    def apply_limits_action(self, request, queryset):
        count = 0
        for dist in queryset:
            dist.apply_limits()
            count += 1
        self.message_user(request, f"Applied limits to {count} distribution(s)")

    @admin.action(description="Retry failed distributions")
    def retry_failed(self, request, queryset):
        from apps.distribution.tasks import distribute_content

        count = 0
        for dist in queryset.filter(status="failed"):
            dist.status = "pending"
            dist.save()
            try:
                distribute_content.delay(dist.id)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"Queued {count} distribution(s) for retry")
