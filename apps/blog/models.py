from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse


class PostStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    summary = models.TextField(blank=True, default="")
    seo_title = models.CharField(max_length=240, blank=True, default="")
    seo_description = models.CharField(max_length=320, blank=True, default="")
    canonical_url = models.URLField(blank=True, default="")
    hero_image = models.URLField(blank=True, default="")
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts"
    )
    tags = models.ManyToManyField("tags.Tag", blank=True, related_name="posts")
    status = models.CharField(
        max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT
    )
    publish_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    reading_time = models.PositiveIntegerField(default=0, help_text="Minutes")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("blog:post_detail", kwargs={"slug": self.slug})

    @property
    def is_live(self) -> bool:
        if self.status == PostStatus.PUBLISHED:
            if self.publish_at:
                return self.publish_at <= timezone.now()
            return True
        if self.status == PostStatus.SCHEDULED and self.publish_at:
            return self.publish_at <= timezone.now()
        return False

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:230]
            candidate = base
            idx = 1
            while Post.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{idx}"
                idx += 1
            self.slug = candidate
        # Normalize status + published timestamps
        if self.status == PostStatus.PUBLISHED:
            self.is_published = True
            if not self.published_at:
                self.published_at = timezone.now()
            if not self.publish_at:
                self.publish_at = self.published_at
        elif self.status == PostStatus.SCHEDULED:
            self.is_published = False
            if self.publish_at and self.publish_at <= timezone.now():
                self.is_published = True
                self.published_at = self.publish_at
        else:
            self.is_published = False

        # Derive SEO title/description fallbacks
        if not self.seo_title:
            self.seo_title = self.title[:240]
        if not self.seo_description and self.summary:
            self.seo_description = self.summary[:320]

        # Estimate reading time (200 wpm)
        words = len(self.body.split())
        self.reading_time = max(1, round(words / 200)) if words else 1

        super().save(*args, **kwargs)


class PostDraft(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_drafts")
    post = models.ForeignKey("blog.Post", null=True, blank=True, on_delete=models.CASCADE, related_name="drafts")
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Draft for {self.post or 'new post'} by {self.user}"


class PostRevision(models.Model):
    post = models.ForeignKey("blog.Post", on_delete=models.CASCADE, related_name="revisions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="post_revisions")
    snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Revision {self.created_at} for {self.post}"
