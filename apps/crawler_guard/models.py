from __future__ import annotations

from django.db import models


class CrawlerRule(models.Model):
    ACTION_CHOICES = [
        ("allow", "Allow"),
        ("throttle", "Throttle"),
        ("block", "Block"),
        ("challenge", "Challenge"),
    ]

    name = models.CharField(max_length=100, unique=True)
    path_pattern = models.CharField(
        max_length=255, help_text="fnmatch-style pattern e.g. /api/*"
    )
    requests_per_minute = models.PositiveIntegerField(default=60)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default="allow")
    is_enabled = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    priority = models.IntegerField(
        default=0, help_text="Higher value wins. Evaluated descending."
    )
    stop_processing = models.BooleanField(
        default=False,
        help_text="If matched and allowed, stop evaluating further rules.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "name"]

    def __str__(self) -> str:  # pragma: no cover - simple display
        return self.name


class CrawlerEvent(models.Model):
    ACTION_CHOICES = CrawlerRule.ACTION_CHOICES

    ip = models.CharField(max_length=45, db_index=True)
    device_identifier = models.CharField(
        max_length=64, blank=True, null=True, db_index=True
    )
    path = models.CharField(max_length=255)
    rule_triggered = models.ForeignKey(
        CrawlerRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    action_taken = models.CharField(
        max_length=20, choices=ACTION_CHOICES, default="allow"
    )
    user_agent = models.TextField(blank=True, default="")
    headers_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip", "created_at"]),
            models.Index(fields=["action_taken"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple display
        return f"{self.ip} -> {self.action_taken}"
