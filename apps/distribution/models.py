
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from solo.models import SingletonModel


class DistributionStatus(models.TextChoices):
    """Status choices for content distribution"""
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    DISTRIBUTING = "distributing", "Distributing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


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
    Centralized configuration for Distribution module with policy-compliant limits.
    Configure all automation limits, SEO constraints, and distribution policies here.
    """

    # ============================================================
    # General Distribution Settings
    # ============================================================
    distribution_enabled = models.BooleanField(
        default=True,
        help_text="Master switch: Enable/disable all content distribution globally."
    )
    auto_fanout_on_publish = models.BooleanField(
        default=True,
        help_text="Automatically queue distribution when blog posts are published. Disable for manual control."
    )
    default_channels = models.JSONField(
        default=list,
        blank=True,
        help_text="Default channels for auto-distribution (empty = use all active channels). Example: ['twitter', 'facebook', 'linkedin']"
    )
    
    # ============================================================
    # Platform & Distribution Limits (Policy Compliance)
    # ============================================================
    max_platforms_per_content = models.PositiveIntegerField(
        default=5,
        help_text="⚠️ CRITICAL: Maximum platforms to distribute to simultaneously. Recommended: 5 or less to avoid spam detection. Higher values risk platform bans."
    )
    distribution_frequency_hours = models.PositiveIntegerField(
        default=4,
        help_text="Minimum hours between auto-distributions for same content. Prevents spam. Recommended: 4-24 hours."
    )
    
    # ============================================================
    # SEO Limits (Search Engine Guidelines)
    # ============================================================
    max_seo_title_length = models.PositiveIntegerField(
        default=60,
        help_text="Maximum characters for SEO titles. Google displays ~60 chars. Longer titles get truncated in search results."
    )
    max_seo_description_length = models.PositiveIntegerField(
        default=160,
        help_text="Maximum characters for meta descriptions. Google displays ~160 chars. Keep it concise for better CTR."
    )
    max_seo_tags = models.PositiveIntegerField(
        default=10,
        help_text="⚠️ Maximum SEO-focused tags per content. Too many tags = keyword stuffing = Google penalty. Recommended: 5-10."
    )
    
    # ============================================================
    # Auto-Tagging Limits (Content Optimization)
    # ============================================================
    max_auto_tags = models.PositiveIntegerField(
        default=15,
        help_text="⚠️ Maximum auto-generated tags per post. Over-tagging reduces content quality. Recommended: 10-15. Platform limits apply."
    )
    auto_tag_frequency_days = models.PositiveIntegerField(
        default=7,
        help_text="How often (in days) to regenerate auto-tags for existing content. Lower = more frequent updates. 0 = never update."
    )
    
    # ============================================================
    # Retry & Error Handling
    # ============================================================
    max_retries = models.PositiveIntegerField(
        default=3,
        help_text="Maximum retry attempts per failed distribution job before marking as permanently failed."
    )
    retry_backoff_seconds = models.PositiveIntegerField(
        default=1800,
        help_text="Wait time (seconds) before retrying a failed job. 1800s = 30 minutes. Use exponential backoff for rate limits."
    )
    
    # ============================================================
    # Advanced Features
    # ============================================================
    allow_indexing_jobs = models.BooleanField(
        default=False,
        help_text="Allow automatic submission to search engines (Google/Bing indexing APIs). Requires API keys. Disable if not configured."
    )
    require_admin_approval = models.BooleanField(
        default=False,
        help_text="Require manual admin approval before executing distribution jobs. Good for auditing but slows automation."
    )
    enable_firmware_auto_distribution = models.BooleanField(
        default=True,
        help_text="Auto-distribute firmware blog posts when created/updated. Disable to distribute firmware posts manually only."
    )

    class Meta:
        verbose_name = "Distribution Settings"
        verbose_name_plural = "Distribution Settings"

    def __str__(self) -> str:
        return "Distribution Settings"
    
    def get_limits_summary(self):
        """Return a summary of current limits for display"""
        return {
            'platforms': self.max_platforms_per_content,
            'seo_tags': self.max_seo_tags,
            'auto_tags': self.max_auto_tags,
            'seo_title': self.max_seo_title_length,
            'seo_description': self.max_seo_description_length,
            'frequency_hours': self.distribution_frequency_hours,
        }


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


class ContentDistribution(models.Model):
    """
    Generic distribution tracker for any content type (blog posts, firmware updates, etc.)
    Manages multi-platform publishing with policy-compliant limits from DistributionSettings.
    
    This model tracks individual distribution jobs, while DistributionSettings provides
    the global configuration and limits.
    """
    # Generic relation to any content type
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Distribution metadata
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True, default="")
    content_url = models.URLField(blank=True, default="")
    
    # Target channels for distribution
    target_channels = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of channels to distribute to (twitter, linkedin, facebook, etc.)"
    )
    
    # Distribution status and tracking
    status = models.CharField(
        max_length=20,
        choices=DistributionStatus.choices,
        default=DistributionStatus.PENDING
    )
    
    # Distribution settings (inherits from DistributionSettings by default)
    priority = models.PositiveIntegerField(default=5, help_text="1=highest, 10=lowest")
    schedule_at = models.DateTimeField(null=True, blank=True, help_text="Schedule distribution for later")
    
    # Tracking fields
    distributed_at = models.DateTimeField(null=True, blank=True)
    distribution_count = models.PositiveIntegerField(default=0, help_text="Number of successful distributions")
    failed_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional distribution metadata")
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="content_distributions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'schedule_at']),
            models.Index(fields=['priority', 'created_at']),
        ]
        verbose_name = "Content Distribution"
        verbose_name_plural = "Content Distributions"
    
    def __str__(self):
        return f"Distribution: {self.title} ({self.get_status_display()})"
    
    def get_settings(self):
        """Get global distribution settings"""
        return DistributionSettings.get_solo()
    
    def is_ready_for_distribution(self):
        """Check if content is ready to be distributed"""
        if self.status not in [DistributionStatus.PENDING, DistributionStatus.QUEUED]:
            return False
        
        if self.schedule_at and self.schedule_at > timezone.now():
            return False
        
        # Check frequency limit
        if self.distributed_at:
            settings = self.get_settings()
            hours_since_last = (timezone.now() - self.distributed_at).total_seconds() / 3600
            if hours_since_last < settings.distribution_frequency_hours:
                return False
        
        return True
    
    def mark_completed(self):
        """Mark distribution as completed"""
        self.status = DistributionStatus.COMPLETED
        self.distributed_at = timezone.now()
        self.distribution_count += 1
        self.save(update_fields=['status', 'distributed_at', 'distribution_count', 'updated_at'])
    
    def mark_failed(self, error_message):
        """Mark distribution as failed with error message"""
        self.status = DistributionStatus.FAILED
        self.failed_count += 1
        self.last_error = error_message
        self.save(update_fields=['status', 'failed_count', 'last_error', 'updated_at'])
    
    def apply_limits(self):
        """
        Apply policy-compliant limits from DistributionSettings to prevent over-distribution.
        This ensures all content respects the configured limits in admin panel.
        """
        settings = self.get_settings()
        
        # Limit target channels based on admin configuration
        if len(self.target_channels) > settings.max_platforms_per_content:
            self.target_channels = self.target_channels[:settings.max_platforms_per_content]
        
        # Check metadata for tags and apply limits from settings
        if 'tags' in self.metadata:
            tags = self.metadata['tags']
            if len(tags) > settings.max_auto_tags:
                self.metadata['tags'] = tags[:settings.max_auto_tags]
        
        if 'seo_tags' in self.metadata:
            seo_tags = self.metadata['seo_tags']
            if len(seo_tags) > settings.max_seo_tags:
                self.metadata['seo_tags'] = seo_tags[:settings.max_seo_tags]
        
        # Truncate title and summary to SEO limits
        if len(self.title) > settings.max_seo_title_length:
            self.title = self.title[:settings.max_seo_title_length - 3] + '...'
        
        if len(self.summary) > settings.max_seo_description_length:
            self.summary = self.summary[:settings.max_seo_description_length - 3] + '...'
        
        self.save()


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



