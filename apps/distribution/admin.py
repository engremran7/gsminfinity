
from __future__ import annotations

from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django import forms
from django.db import models
from django.utils import timezone

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
    raise ImproperlyConfigured("django-solo is required for DistributionSettings admin") from exc


@admin.register(DistributionSettings)
class DistributionSettingsAdmin(SingletonModelAdmin):
    list_display = ("distribution_enabled", "auto_fanout_on_publish", "max_retries", "require_admin_approval")
    fieldsets = (
        (None, {"fields": ("distribution_enabled", "auto_fanout_on_publish", "require_admin_approval")}),
        (
            "Channels & Indexing",
            {"fields": ("default_channels", "allow_indexing_jobs")},
        ),
        ("Retries & Backoff", {"fields": ("max_retries", "retry_backoff_seconds")}),
    )

    def has_add_permission(self, request):
        return False


