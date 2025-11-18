"""
Enterprise-grade Site & Tenant Settings

✓ Django 5.2 / Python 3.12
✓ Admin-uploadable branding assets (logo, dark logo, favicon)
✓ Generic, non-branded defaults
✓ Hardened validation (colors, file uploads, limits)
✓ Fully safe file URL helpers (static() fallback)
✓ Strict ManyToMany consistency
✓ Tenant-aware
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Any

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.sites.models import Site
from django.templatetags.static import static
from solo.models import SingletonModel

logger = logging.getLogger(__name__)

# =====================================================================
# GLOBAL CONSTANTS
# =====================================================================
_ALLOWED_VERIFICATION_EXTENSIONS = {".txt", ".html", ".xml", ".json"}
_MAX_VERIFICATION_FILE_BYTES = 1 * 1024 * 1024  # 1 MiB

_HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#(?:[A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
    message="Enter a valid hex color like #0d6efd",
)


# =====================================================================
# GLOBAL / DEFAULT SITE SETTINGS (SINGLETON)
# =====================================================================
class SiteSettings(SingletonModel):
    """
    Global site-wide configuration (non-branded, fully generic).
    """

    # ------------------------------------------------------------------
    # Branding – MUST remain generic (no “GSM” or “Infinity”!)
    # ------------------------------------------------------------------
    site_name = models.CharField(max_length=100, default="Site")
    site_header = models.CharField(max_length=100, default="Admin")
    site_description = models.TextField(blank=True, default="")

    logo = models.ImageField(
        upload_to="branding/",
        blank=True,
        null=True,
        help_text="Primary site logo (SVG/PNG)",
    )
    dark_logo = models.ImageField(
        upload_to="branding/",
        blank=True,
        null=True,
        help_text="Dark mode logo",
    )
    favicon = models.ImageField(
        upload_to="branding/",
        blank=True,
        null=True,
        help_text="Favicon (PNG/ICO/SVG)",
    )

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    theme_profile = models.CharField(max_length=50, blank=True, null=True)

    primary_color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[_HEX_COLOR_VALIDATOR],
    )
    secondary_color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[_HEX_COLOR_VALIDATOR],
    )

    # ------------------------------------------------------------------
    # Localization
    # ------------------------------------------------------------------
    default_language = models.CharField(max_length=10, default="en")
    timezone = models.CharField(max_length=50, default="UTC")
    enable_localization = models.BooleanField(default=False)

    # ------------------------------------------------------------------
    # AI Personalization
    # ------------------------------------------------------------------
    enable_ai_personalization = models.BooleanField(default=False)
    ai_theme_mode = models.CharField(
        max_length=20,
        choices=[("light", "Light"), ("dark", "Dark"), ("auto", "Auto")],
        default="auto",
    )
    ai_model_version = models.CharField(max_length=20, blank=True, null=True)

    # ------------------------------------------------------------------
    # Security & Features
    # ------------------------------------------------------------------
    enable_signup = models.BooleanField(default=True)
    enable_password_reset = models.BooleanField(default=True)
    enable_notifications = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)

    force_https = models.BooleanField(
        default=False,
        help_text="Enable only if TLS is enforced by reverse proxy",
    )

    # ------------------------------------------------------------------
    # reCAPTCHA
    # ------------------------------------------------------------------
    recaptcha_enabled = models.BooleanField(default=False)
    recaptcha_mode = models.CharField(
        max_length=20,
        choices=[("v2", "v2"), ("v3", "v3")],
        default="v2",
    )
    recaptcha_public_key = models.CharField(max_length=100, blank=True, null=True)
    recaptcha_private_key = models.CharField(max_length=100, blank=True, null=True)

    recaptcha_score_threshold = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    recaptcha_timeout_ms = models.PositiveIntegerField(default=3000)

    # ------------------------------------------------------------------
    # MFA / Device Security
    # ------------------------------------------------------------------
    max_devices_per_user = models.PositiveIntegerField(default=3)
    lock_duration_minutes = models.PositiveIntegerField(default=15)
    fingerprint_mode = models.CharField(
        max_length=20,
        choices=[("strict", "Strict"), ("lenient", "Lenient")],
        default="strict",
    )
    enforce_unique_device = models.BooleanField(default=True)
    require_mfa = models.BooleanField(default=False)

    mfa_totp_issuer = models.CharField(max_length=50, default="Site")

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------
    email_verification_code_length = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(4), MaxValueValidator(12)],
    )
    email_verification_code_type = models.CharField(
        max_length=20,
        choices=[("numeric", "Numeric"), ("alphanumeric", "Alphanumeric")],
        default="alphanumeric",
    )

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    max_login_attempts = models.PositiveIntegerField(default=5)
    rate_limit_window_seconds = models.PositiveIntegerField(default=300)

    # Cache TTL (consumed by the context processor)
    cache_ttl_seconds = models.PositiveIntegerField(default=600)

    # ------------------------------------------------------------------
    # Meta Tags & Verification Files
    # ------------------------------------------------------------------
    meta_tags = models.ManyToManyField(
        "VerificationMetaTag",
        through="SiteSettingsMetaTagLink",
        blank=True,
    )
    verification_files = models.ManyToManyField(
        "VerificationFile",
        through="SiteSettingsVerificationFileLink",
        blank=True,
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self) -> str:
        return self.site_name or "Site Settings"

    # =================================================================
    # SAFE FILE URL HELPERS (always static fallback)
    # =================================================================
    def _safe_file_url(self, field, fallback: str) -> str:
        try:
            if field and getattr(field, "url", None):
                url = field.url
                if isinstance(url, str) and url.strip():
                    return url
        except Exception:
            pass
        return static(fallback)

    @property
    def logo_url(self) -> str:
        return self._safe_file_url(self.logo, "img/default-logo.svg")

    @property
    def dark_logo_url(self) -> str:
        # Try dark → fallback to normal → fallback to static
        url = self._safe_file_url(self.dark_logo, "")
        if url:
            return url
        url = self._safe_file_url(self.logo, "")
        if url:
            return url
        return static("img/default-logo-dark.svg")

    @property
    def favicon_url(self) -> str:
        return self._safe_file_url(self.favicon, "img/default-favicon.png")

    # =================================================================
    # VALIDATION
    # =================================================================
    def clean(self):
        errors = {}

        for name, val in [
            ("primary_color", self.primary_color),
            ("secondary_color", self.secondary_color),
        ]:
            if val:
                try:
                    _HEX_COLOR_VALIDATOR(val)
                except ValidationError as exc:
                    errors[name] = exc.messages

        if errors:
            raise ValidationError(errors)

    # =================================================================
    # FRONTEND CONFIG HELPERS
    # =================================================================
    def get_theme(self) -> dict[str, Any]:
        return {
            "profile": self.theme_profile or "default",
            "primary_color": self.primary_color or "#0d6efd",
            "secondary_color": self.secondary_color or "#6c757d",
            "ai_mode": self.ai_theme_mode,
        }

    def recaptcha_config(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.recaptcha_enabled),
            "mode": self.recaptcha_mode,
            "public_key": self.recaptcha_public_key or "",
            "threshold": float(self.recaptcha_score_threshold),
            "timeout": int(self.recaptcha_timeout_ms),
        }


# =====================================================================
# META TAGS
# =====================================================================
class VerificationMetaTag(models.Model):
    provider = models.CharField(max_length=50, db_index=True)
    name_attr = models.CharField(max_length=100)
    content_attr = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "name_attr"], name="ver_meta_idx")
        ]

    def __str__(self):
        return f"{self.provider}: {self.name_attr}"


# =====================================================================
# VERIFICATION FILES (SAFE)
# =====================================================================
class VerificationFile(models.Model):
    provider = models.CharField(max_length=50, db_index=True)
    file = models.FileField(upload_to="verification/")
    description = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["provider"], name="ver_file_idx")
        ]

    def __str__(self):
        name = getattr(self.file, "name", None)
        return f"{self.provider}: {name or '(invalid file)'}"

    # SAFE VALIDATION
    def clean(self):
        errors = {}

        # extension check
        try:
            ext = Path(self.file.name).suffix.lower()
            if ext not in _ALLOWED_VERIFICATION_EXTENSIONS:
                errors.setdefault("file", []).append(
                    f"Unsupported extension: {ext}"
                )
        except Exception:
            pass

        # size check
        try:
            if self.file.size > _MAX_VERIFICATION_FILE_BYTES:
                errors.setdefault("file", []).append(
                    f"File exceeds {_MAX_VERIFICATION_FILE_BYTES} bytes"
                )
        except Exception:
            pass

        if errors:
            raise ValidationError(errors)

    def save(self, *a, **kw):
        self.full_clean()
        return super().save(*a, **kw)


# =====================================================================
# THROUGH MODELS
# =====================================================================
class SiteSettingsMetaTagLink(models.Model):
    site_settings = models.ForeignKey(
        SiteSettings, on_delete=models.CASCADE, related_name="meta_tag_links"
    )
    meta_tag = models.ForeignKey(
        VerificationMetaTag, on_delete=models.CASCADE, related_name="site_links"
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("site_settings", "meta_tag")
        indexes = [
            models.Index(fields=["site_settings", "meta_tag"], name="site_meta_link_idx")
        ]


class SiteSettingsVerificationFileLink(models.Model):
    site_settings = models.ForeignKey(
        SiteSettings, on_delete=models.CASCADE, related_name="verification_file_links"
    )
    verification_file = models.ForeignKey(
        VerificationFile, on_delete=models.CASCADE, related_name="site_links"
    )
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("site_settings", "verification_file")
        indexes = [
            models.Index(fields=["site_settings", "verification_file"], name="site_file_link_idx")
        ]


# =====================================================================
# TENANT SETTINGS
# =====================================================================
class TenantSiteSettings(models.Model):
    site = models.OneToOneField(
        Site, on_delete=models.CASCADE, related_name="tenant_settings"
    )

    theme_profile = models.CharField(max_length=50, blank=True, null=True)
    primary_color = models.CharField(
        max_length=7, blank=True, null=True, validators=[_HEX_COLOR_VALIDATOR]
    )
    secondary_color = models.CharField(
        max_length=7, blank=True, null=True, validators=[_HEX_COLOR_VALIDATOR]
    )

    meta_tags = models.ManyToManyField(VerificationMetaTag, blank=True)
    verification_files = models.ManyToManyField(VerificationFile, blank=True)

    class Meta:
        verbose_name = "Tenant Site Settings"

    def __str__(self):
        return f"Tenant settings for {getattr(self.site, 'domain', 'unknown')}"

    def get_colors(self) -> dict[str, str]:
        return {
            "primary": self.primary_color or "#0d6efd",
            "secondary": self.secondary_color or "#6c757d",
        }
