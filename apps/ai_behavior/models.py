from __future__ import annotations

from django.conf import settings
from django.db import models


class BehaviorInsight(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("resolved", "Resolved"),
    ]

    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="behavior_insights",
    )
    device_identifier = models.CharField(
        max_length=64, blank=True, null=True, db_index=True
    )
    related_ip = models.CharField(max_length=45, blank=True, null=True, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="low")
    recommendation = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["severity"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.severity} insight ({self.status})"
