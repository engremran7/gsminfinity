from django.conf import settings
from django.db import models
from solo.models import SingletonModel


class TimestampedModel(models.Model):
    """
    Minimal timestamp mixin for models that do not need soft-delete/audit.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Soft-delete abstraction (opt-in per concrete model).
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_deleted",
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None, commit: bool = True) -> None:
        # Stable, timezone-aware soft delete that never surprises callers.
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user and not self.deleted_by:
            self.deleted_by = user
        if commit:
            self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


class AuditFieldsModel(models.Model):
    """
    Adds created_by / updated_by without forcing concrete relations to use them.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True


class AppRegistry(SingletonModel):
    """
    Admin-controlled feature toggles for micro-apps.
    Use these instead of duplicating booleans in SiteSettings.
    """

    seo_enabled = models.BooleanField(
        default=True,
        help_text="Turn SEO module on/off (meta tags, schema, link tools).",
    )
    ads_enabled = models.BooleanField(
        default=True, help_text="Turn Ads module on/off (slots, rotation, tracking)."
    )
    tags_enabled = models.BooleanField(
        default=True,
        help_text="Turn Tags module on/off (taxonomy, tag pages, tag APIs).",
    )
    blog_enabled = models.BooleanField(
        default=True, help_text="Turn Blog module on/off (posts, feeds, public views)."
    )
    comments_enabled = models.BooleanField(
        default=True, help_text="Turn Comments module on/off (API + moderation UI)."
    )
    distribution_enabled = models.BooleanField(
        default=True, help_text="Turn Distribution module on/off (syndication/sharing)."
    )
    users_enabled = models.BooleanField(
        default=True,
        help_text="Turn Users module on/off (auth, profile, notifications).",
    )
    device_identity_enabled = models.BooleanField(
        default=True,
        help_text="Turn Device Identity on/off (fingerprint/login policy).",
    )
    crawler_guard_enabled = models.BooleanField(
        default=True, help_text="Turn Crawler Guard on/off (anti-scraping middleware)."
    )
    ai_behavior_enabled = models.BooleanField(
        default=True, help_text="Turn AI Behavior Engine on/off (risk insights)."
    )
    i18n_themes_enabled = models.BooleanField(
        default=True,
        help_text="Turn i18n + Themes on/off (runtime tokens + translations).",
    )
    ai_enabled = models.BooleanField(
        default=True,
        help_text="Turn AI Platform on/off (models, workflows, knowledge).",
    )

    class Meta:
        verbose_name = "App Registry"

    def __str__(self) -> str:
        return "App Registry"
