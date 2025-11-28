from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel, SoftDeleteModel, AuditFieldsModel


class AdPlacement(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    """
    Represents a slot in the UI. Auto-created by scan_ad_placements.
    """

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(
        max_length=120,
        unique=True,
        help_text="Stable placement code used in templates and auto-discovery.",
    )
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True, default="")
    allowed_types = models.CharField(
        max_length=100,
        blank=True,
        default="banner,native,html",
        help_text="Comma separated types",
    )
    allowed_sizes = models.CharField(
        max_length=100, blank=True, default="", help_text="e.g. 300x250,728x90"
    )
    context = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Page context e.g. blog_detail, blog_list, homepage",
    )
    page_context = models.CharField(max_length=100, blank=True, default="")
    template_reference = models.CharField(max_length=255, blank=True, default="")
    is_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    locked = models.BooleanField(default=False, help_text="Lock to prevent auto changes")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Campaign(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    type = models.CharField(
        max_length=20,
        choices=[
            ("direct", "Direct"),
            ("affiliate", "Affiliate"),
            ("network", "Network"),
            ("house", "House"),
        ],
        default="direct",
    )
    ad_network = models.CharField(max_length=100, blank=True, default="")
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    daily_cap = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    total_cap = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    priority = models.IntegerField(default=0, help_text="Higher wins ties")
    weight = models.PositiveIntegerField(default=1)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    targeting_rules = models.JSONField(default=dict, blank=True)
    locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def is_live(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.start_at and self.start_at > now:
            return False
        if self.end_at and self.end_at < now:
            return False
        return True


class AdCreative(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    CREATIVE_TYPES = [
        ("banner", "Banner"),
        ("native", "Native"),
        ("html", "HTML/JS"),
        ("script", "Script"),
    ]
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="creatives"
    )
    name = models.CharField(max_length=150)
    creative_type = models.CharField(max_length=20, choices=CREATIVE_TYPES)
    html = models.TextField(blank=True, default="")
    html_code = models.TextField(blank=True, default="")
    script_code = models.TextField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    click_url = models.URLField(blank=True, default="")
    tracking_params = models.JSONField(default=dict, blank=True)
    weight = models.PositiveIntegerField(default=1)
    is_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["campaign", "name"]

    def __str__(self):
        return f"{self.campaign}: {self.name}"


class PlacementAssignment(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    placement = models.ForeignKey(
        AdPlacement, on_delete=models.CASCADE, related_name="assignments"
    )
    creative = models.ForeignKey(
        AdCreative, on_delete=models.CASCADE, related_name="assignments"
    )
    weight = models.PositiveIntegerField(default=1)
    is_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("placement", "creative")

    def __str__(self):
        return f"{self.placement} -> {self.creative}"


class AffiliateSource(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    name = models.CharField(max_length=100, unique=True)
    network = models.CharField(max_length=100, blank=True, default="")
    base_url = models.URLField(blank=True, default="")
    is_enabled = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)
    tracking_parameters = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class AffiliateLink(TimestampedModel, SoftDeleteModel, AuditFieldsModel):
    source = models.ForeignKey(
        AffiliateSource, on_delete=models.CASCADE, related_name="links"
    )
    name = models.CharField(max_length=150)
    target_url = models.URLField(blank=True, default="")
    affiliate_url = models.URLField(blank=True, default="")
    slug = models.SlugField(max_length=180, blank=True, db_index=True)
    tags = models.ManyToManyField("tags.Tag", blank=True, related_name="affiliate_links")
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    url = models.URLField()
    is_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("source", "name")

    def __str__(self):
        return f"{self.source} - {self.name}"


class AdEvent(TimestampedModel):
    EVENT_TYPES = [
        ("impression", "Impression"),
        ("click", "Click"),
    ]
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    placement = models.ForeignKey(
        AdPlacement, on_delete=models.SET_NULL, null=True, blank=True
    )
    creative = models.ForeignKey(
        AdCreative, on_delete=models.SET_NULL, null=True, blank=True
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    request_meta = models.JSONField(default=dict, blank=True)
    page_url = models.URLField(blank=True, default="")
    referrer_url = models.URLField(blank=True, default="")
    user_agent = models.TextField(blank=True, default="")
    session_id = models.CharField(max_length=128, blank=True, default="")
    site_domain = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["campaign"]),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}"
