from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Page(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]
    ACCESS_CHOICES = [
        ("public", "Public"),
        ("auth", "Authenticated"),
        ("staff", "Staff"),
    ]
    CHANGEFREQ_CHOICES = [
        ("always", "always"),
        ("hourly", "hourly"),
        ("daily", "daily"),
        ("weekly", "weekly"),
        ("monthly", "monthly"),
        ("yearly", "yearly"),
        ("never", "never"),
    ]

    slug = models.SlugField(unique=True, max_length=200)
    title = models.CharField(max_length=200)
    content = models.TextField()
    content_format = models.CharField(
        max_length=8,
        choices=[("md", "Markdown"), ("html", "HTML")],
        default="md",
    )

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="draft")
    publish_at = models.DateTimeField(null=True, blank=True)
    unpublish_at = models.DateTimeField(null=True, blank=True)

    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    og_image = models.ImageField(upload_to="pages/og/", null=True, blank=True)

    access_level = models.CharField(max_length=12, choices=ACCESS_CHOICES, default="public")

    include_in_sitemap = models.BooleanField(default=True)
    changefreq = models.CharField(max_length=12, choices=CHANGEFREQ_CHOICES, default="weekly")
    priority = models.DecimalField(max_digits=2, decimal_places=1, default=0.5)

    canonical_url = models.URLField(blank=True, default="")
    last_modified = models.DateTimeField(auto_now=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pages_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pages_updated",
    )

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.title or self.slug

    @property
    def is_published(self) -> bool:
        now = timezone.now()
        if self.status != "published":
            return False
        if self.publish_at and self.publish_at > now:
            return False
        if self.unpublish_at and self.unpublish_at <= now:
            return False
        return True
