from __future__ import annotations

from django.conf import settings
from django.db import models


class SecurityEvent(models.Model):
    type = models.CharField(max_length=64)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="security_events"
    )
    device = models.ForeignKey(
        "devices.Device", null=True, blank=True, on_delete=models.SET_NULL, related_name="security_events"
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["type"], name="security_event_type_idx"),
            models.Index(fields=["created_at"], name="security_event_created_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - human display only
        return f"{self.type} @ {self.created_at}"
