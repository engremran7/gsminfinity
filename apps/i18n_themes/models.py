
from __future__ import annotations

from django.conf import settings
from django.db import models


class Locale(models.Model):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64)
    direction = models.CharField(
        max_length=3,
        choices=[("ltr", "LTR"), ("rtl", "RTL")],
        default="ltr",
    )
    enabled_global = models.BooleanField(default=True)
    enabled_for_apps = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.direction})"


class LanguageProfile(models.Model):
    app_id = models.CharField(max_length=64, db_index=True)
    site_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    default_locale = models.CharField(max_length=16, default="en")
    supported_locales = models.JSONField(default=list, blank=True)
    fallback_locale = models.CharField(max_length=16, default="en")

    class Meta:
        unique_together = ("app_id", "site_id")
        indexes = [models.Index(fields=["app_id", "site_id"])]

    def __str__(self) -> str:
        return f"{self.app_id}:{self.site_id or 'global'}"


class TranslationKey(models.Model):
    WORKFLOW_CHOICES = [
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("deprecated", "Deprecated"),
    ]

    app_id = models.CharField(max_length=64, db_index=True)
    namespace = models.CharField(max_length=64, default="common", db_index=True)
    key = models.CharField(max_length=256, db_index=True)
    context = models.TextField(blank=True, default="")
    workflow_state = models.CharField(max_length=20, choices=WORKFLOW_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="i18n_keys_created",
    )

    class Meta:
        unique_together = ("app_id", "namespace", "key")
        indexes = [
            models.Index(fields=["app_id", "namespace", "key"]),
        ]

    def __str__(self) -> str:
        return f"{self.app_id}:{self.namespace}:{self.key}"


class TranslationValue(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("deprecated", "Deprecated"),
    ]

    translation_key = models.ForeignKey(TranslationKey, on_delete=models.CASCADE, related_name="values")
    locale = models.CharField(max_length=16, db_index=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="i18n_values_updated",
    )

    class Meta:
        unique_together = ("translation_key", "locale")
        indexes = [models.Index(fields=["locale", "status"])]

    def __str__(self) -> str:
        return f"{self.translation_key} [{self.locale}]"


class MissingKeyLog(models.Model):
    app_id = models.CharField(max_length=64, db_index=True)
    site_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    locale = models.CharField(max_length=16, db_index=True)
    key = models.CharField(max_length=256, db_index=True)
    route = models.CharField(max_length=256, blank=True, default="")
    user_id = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["app_id", "locale"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.app_id}:{self.key}:{self.locale}"


class FontRegistry(models.Model):
    code = models.CharField(max_length=64, unique=True)
    family = models.CharField(max_length=128)
    urls = models.JSONField(default=list, blank=True)
    weight_map = models.JSONField(default=dict, blank=True)
    font_display = models.CharField(max_length=16, default="swap")
    is_default_for_locales = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.family


class Theme(models.Model):
    MODE_CHOICES = [
        ("light", "Light"),
        ("dark", "Dark"),
        ("high_contrast", "High Contrast"),
    ]

    app_id = models.CharField(max_length=64, db_index=True)
    site_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=100)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="light")
    inherits_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    tokens = models.JSONField(default=dict, blank=True)
    locale_overrides = models.JSONField(default=dict, blank=True)
    is_locked = models.BooleanField(default=False, help_text="Prevents overriding core brand tokens.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("app_id", "site_id", "name", "mode")
        indexes = [
            models.Index(fields=["app_id", "site_id", "mode"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.mode})"


class ThemeAssignment(models.Model):
    SCOPE_CHOICES = [
        ("global", "Global"),
        ("site", "Site"),
        ("route", "Route"),
        ("user", "User"),
        ("device", "Device Preference"),
        ("system", "System Preference"),
    ]

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="assignments")
    app_id = models.CharField(max_length=64, db_index=True)
    site_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    route = models.CharField(max_length=256, blank=True, null=True)
    user_id = models.CharField(max_length=64, blank=True, null=True)
    device_pref = models.CharField(max_length=20, blank=True, null=True)
    system_pref = models.CharField(max_length=20, blank=True, null=True)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES, default="global")

    class Meta:
        indexes = [
            models.Index(fields=["app_id", "site_id", "scope"]),
        ]

    def __str__(self) -> str:
        return f"{self.theme} -> {self.scope}"


class AppManifest(models.Model):
    app_id = models.CharField(max_length=64, unique=True)
    site_id = models.CharField(max_length=64, blank=True, null=True)
    namespaces = models.JSONField(default=list, blank=True)
    token_usage = models.JSONField(default=list, blank=True)
    supported_locales = models.JSONField(default=list, blank=True)
    default_locale = models.CharField(max_length=16, default="en")
    routes = models.JSONField(default=list, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["app_id"])]

    def __str__(self) -> str:
        return f"Manifest:{self.app_id}"


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="i18n_theme_audits",
    )
    action = models.CharField(max_length=64)
    app_id = models.CharField(max_length=64, blank=True, null=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} @ {self.created_at}"


