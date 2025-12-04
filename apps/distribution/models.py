
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from solo.models import SingletonModel


class Channel(models.TextChoices):
    TWITTER = "twitter", "Twitter / X"
    LINKEDIN = "linkedin", "LinkedIn"
    FACEBOOK = "facebook", "Facebook Pages"
    INSTAGRAM = "instagram", "Instagram"
    PINTEREST = "pinterest", "Pinterest"
    REDDIT = "reddit", "Reddit"
    TIKTOK = "tiktok", "TikTok"
    TELEGRAM = "telegram", "Telegram"
    DISCORD = "discord", "Discord"
    SLACK = "slack", "Slack"
    WHATSAPP = "whatsapp", "WhatsApp"
    DEVTO = "devto", "Dev.to"
    HASHNODE = "hashnode", "Hashnode"
    MEDIUM = "medium", "Medium"
    GITHUB_GIST = "gist", "GitHub Gist"
    MAILCHIMP = "mailchimp", "Mailchimp"
    SENDGRID = "sendgrid", "SendGrid"
    SUBSTACK = "substack", "Substack"
    INDEXING_GOOGLE = "google_indexing", "Google Indexing API"
    INDEXING_BING = "bing_indexing", "Bing URL Submit"
    AI_CHATGPT = "chatgpt_action", "ChatGPT Action"
    AI_GEMINI = "gemini", "Google Gemini"
    AI_COPILOT = "copilot", "Bing Copilot"
    RSS = "rss", "RSS"
    ATOM = "atom", "Atom"
    JSON = "json", "JSON Feed"
    WEBSUB = "websub", "WebSub"


class SocialAccount(models.Model):
    channel = models.CharField(max_length=64, choices=Channel.choices)
    account_name = models.CharField(max_length=200, blank=True, default="")
    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="social_accounts",
    )

    class Meta:
        ordering = ["channel", "account_name"]
        unique_together = [("channel", "account_name")]

    def __str__(self) -> str:
        return f"{self.get_channel_display()}:{self.account_name or self.pk}"

    @property
    def is_expired(self) -> bool:
        return bool(self.token_expires_at and self.token_expires_at <= timezone.now())


class ShareTemplate(models.Model):
    channel = models.CharField(max_length=64, choices=Channel.choices)
    name = models.CharField(max_length=120)
    body_template = models.TextField(
        help_text="Use placeholders: {title}, {url}, {summary}, {hashtags}"
    )
    media_template = models.TextField(blank=True, default="")
    ai_prompt = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["channel", "name"]
        unique_together = [("channel", "name")]

    def __str__(self) -> str:
        return f"{self.get_channel_display()}::{self.name}"


class ContentVariant(models.Model):
    VARIANT_TYPES = (
        ("summary", "Summary"),
        ("caption", "Caption"),
        ("tags", "Hashtags/Tags"),
        ("image_prompt", "Image prompt"),
        ("thread", "Thread/long-form"),
        ("email", "Email"),
    )

    post = models.ForeignKey("blog.Post", on_delete=models.CASCADE, related_name="variants")
    channel = models.CharField(max_length=64, choices=Channel.choices)
    variant_type = models.CharField(max_length=32, choices=VARIANT_TYPES)
    payload = models.JSONField(default=dict, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_variants",
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        unique_together = [("post", "channel", "variant_type")]

    def __str__(self) -> str:
        return f"{self.post_id}:{self.channel}:{self.variant_type}"


class SharePlan(models.Model):
    post = models.ForeignKey("blog.Post", on_delete=models.CASCADE, related_name="share_plans")
    channels = models.JSONField(default=list, blank=True, help_text="List of channel identifiers")
    schedule_at = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=10)
    status = models.CharField(
        max_length=32,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="share_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Plan:{self.post_id}:{self.status}"


class ShareJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    post = models.ForeignKey("blog.Post", on_delete=models.CASCADE, related_name="share_jobs")
    plan = models.ForeignKey(SharePlan, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    account = models.ForeignKey(SocialAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="jobs")
    channel = models.CharField(max_length=64, choices=Channel.choices)
    payload = models.JSONField(default=dict, blank=True)
    schedule_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    external_post_id = models.CharField(max_length=200, blank=True, default="")
    correlation_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["schedule_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel}:{self.post_id}:{self.status}"


class ShareLog(models.Model):
    job = models.ForeignKey(ShareJob, on_delete=models.CASCADE, related_name="logs")
    level = models.CharField(max_length=16, default="info")
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    response_code = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.job_id}:{self.level}"


class DistributionSettings(SingletonModel):
    """
    Per-app settings for the Distribution module.
    """

    distribution_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Distribution Settings"

    def __str__(self) -> str:
        return "Distribution Settings"


class WebSubSubscription(models.Model):
    topic_url = models.URLField()
    hub_url = models.URLField()
    secret = models.CharField(max_length=200, blank=True, default="")
    lease_seconds = models.PositiveIntegerField(default=864000)  # 10 days
    active = models.BooleanField(default=True)
    last_challenge_at = models.DateTimeField(null=True, blank=True)
    last_pinged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("topic_url", "hub_url")]

    def __str__(self) -> str:
        return f"WebSub:{self.topic_url}"


class SyndicationPartner(models.Model):
    name = models.CharField(max_length=120, unique=True)
    endpoint = models.URLField()
    auth_type = models.CharField(
        max_length=32,
        choices=[
            ("none", "None"),
            ("token", "Token"),
            ("basic", "Basic"),
            ("api_key", "API Key"),
        ],
        default="none",
    )
    format = models.CharField(
        max_length=32,
        choices=[
            ("rss", "RSS"),
            ("json", "JSON Feed"),
            ("api", "Custom API"),
            ("graphql", "GraphQL"),
        ],
        default="rss",
    )
    headers = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"Syndication:{self.name}"


