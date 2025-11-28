from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import AuditFieldsModel, SoftDeleteModel, TimestampedModel


class SEOModel(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    """
    Generic container for SEO-related data tied to any model instance.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    locked = models.BooleanField(default=False)
    ai_generated = models.BooleanField(default=False)

    class Meta:
        unique_together = ("content_type", "object_id")


class Metadata(TimestampedModel):
    seo = models.OneToOneField(
        SEOModel, on_delete=models.CASCADE, related_name="metadata"
    )
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.CharField(max_length=320, blank=True, default="")
    focus_keywords = models.JSONField(default=list, blank=True)
    canonical_url = models.URLField(blank=True, default="")
    robots_directives = models.CharField(max_length=255, blank=True, default="")
    social_title = models.CharField(max_length=255, blank=True, default="")
    social_description = models.CharField(max_length=320, blank=True, default="")
    social_image = models.URLField(blank=True, default="")
    noindex = models.BooleanField(default=False)
    nofollow = models.BooleanField(default=False)
    content_hash = models.CharField(max_length=64, blank=True, default="")
    ai_score = models.FloatField(default=0.0)
    schema_json = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)


class SchemaEntry(TimestampedModel):
    seo = models.ForeignKey(
        SEOModel, on_delete=models.CASCADE, related_name="schemas"
    )
    schema_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    locked = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)


class SitemapEntry(TimestampedModel):
    url = models.URLField(unique=True)
    lastmod = models.DateTimeField(null=True, blank=True)
    changefreq = models.CharField(max_length=20, blank=True, default="")
    priority = models.FloatField(default=0.5)
    is_active = models.BooleanField(default=True)
    last_status = models.PositiveIntegerField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class Redirect(TimestampedModel):
    source = models.CharField(max_length=255, unique=True)
    target = models.CharField(max_length=255)
    is_permanent = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["source"]


class LinkableEntity(TimestampedModel):
    """
    Registry of linkable content for internal linking.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, db_index=True)
    aliases = models.JSONField(default=list, blank=True)
    entity_type = models.CharField(max_length=100, blank=True, default="")
    url = models.URLField()
    keywords = models.JSONField(default=list, blank=True)
    embedding = models.BinaryField(null=True, blank=True)
    vector = models.BinaryField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("content_type", "object_id")
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:240]
            self.slug = base or f"entity-{self.pk or ''}"
        super().save(*args, **kwargs)


class LinkSuggestion(TimestampedModel):
    """
    Stable suggestions for internal linking. Not auto-applied unless requested.
    """

    source = models.ForeignKey(
        LinkableEntity, on_delete=models.CASCADE, related_name="suggestions_from"
    )
    target = models.ForeignKey(
        LinkableEntity, on_delete=models.CASCADE, related_name="suggestions_to"
    )
    score = models.FloatField(default=0.0)
    is_applied = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("source", "target")
