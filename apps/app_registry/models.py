
from __future__ import annotations

from django.db import models


class AppEntry(models.Model):
    """
    Central registry of app capabilities, consent, and identity requirements.
    Populated from i18n_themes manifests or explicit registration.
    """

    app_id = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128, blank=True, default="")
    routes = models.JSONField(default=list, blank=True)
    i18n_namespaces = models.JSONField(default=list, blank=True)
    supported_locales = models.JSONField(default=list, blank=True)
    required_consent = models.JSONField(default=list, blank=True, help_text="List of consent scopes required by this app.")
    min_identity_level = models.CharField(
        max_length=16,
        choices=[("none", "None"), ("fallback", "Fallback"), ("primary", "Primary")],
        default="none",
        help_text="Minimum device identity level required (fallback uses server-side FP).",
    )
    feature_flags = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["app_id"]

    def __str__(self) -> str:
        return self.display_name or self.app_id


