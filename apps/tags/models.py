from __future__ import annotations

from django.db import models
from django.utils.text import slugify
from apps.core.models import TimestampedModel, SoftDeleteModel


class Tag(TimestampedModel, SoftDeleteModel):
    name = models.CharField(max_length=64, unique=True, help_text="Use concise, reusable names.")
    normalized_name = models.CharField(max_length=64, blank=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    description = models.TextField(blank=True, default="", help_text="Explain when to use this tag.")
    synonyms = models.JSONField(default=list, blank=True, help_text="Comma-separated alternatives users might search.")
    usage_count = models.PositiveIntegerField(default=0)
    co_occurrence = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    ai_suggested = models.BooleanField(default=False, help_text="True if suggested by AI and not yet curated.")
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.normalized_name:
            self.normalized_name = self.name.lower().strip()
        if not self.slug:
            base = slugify(self.name)[:75]
            candidate = base
            idx = 1
            while Tag.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{idx}"
                idx += 1
            self.slug = candidate
        super().save(*args, **kwargs)
