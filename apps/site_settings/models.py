"""
Site & Tenant Settings Models
=============================
Enterprise configuration module for GSMInfinity.

Provides:
- Singleton global site settings (via django-solo)
- Tenant-specific overrides
- Meta tag and file verification records
- Security, rate-limiting, and AI personalization controls
"""

from django.db import models
from django.contrib.sites.models import Site
from solo.models import SingletonModel


# ============================================================
#  GLOBAL SITE SETTINGS
# ============================================================
class SiteSettings(SingletonModel):
    """
    Singleton model storing enterprise-wide configuration.
    Supports caching via django-solo and automatic fallback in templates.
    """

    # ------------------------------------------------------------
    # Branding & Identity
    # ------------------------------------------------------------
    site_name = models.CharField(max_length=100, default="GsmInfinity")
    site_header = models.CharField(max_length=100, default="GSM Admin")
    site_description = models.TextField(blank=True, default="")
    favicon = models.ImageField(upload_to="branding/", blank=True, null=True)

    # ------------------------------------------------------------
    # Theme & Appearance
    # ------------------------------------------------------------
    theme_profile = models.CharField(max_length=50, blank=True, null=True)
    primary_color = models.CharField(max_length=20, blank=True, null=True)
    secondary_color = models.CharField(max_length=20, blank=True, null=True)

    # ------------------------------------------------------------
    # Locale & Internationalization
    # ------------------------------------------------------------
    default_language = models.CharField(max_length=10, default="en")
    timezone = models.CharField(max_length=50, default="UTC")
    enable_localization = models.BooleanField(default=False)

    # ------------------------------------------------------------
    # AI Personalization
    # ------------------------------------------------------------
    enable_ai_personalization = models.BooleanField(default=False)
    ai_theme_mode = models.CharField(
        max_length=20,
        choices=[("light", "Light"), ("dark", "Dark"), ("auto", "Auto")],
        default="auto",
    )
    ai_model_version = models.CharField(max_length=20, blank=True, null=True)

    # ------------------------------------------------------------
    # Security & Feature Toggles
    # ------------------------------------------------------------
    enable_signup = models.BooleanField(default=True)
    enable_password_reset = models.BooleanField(default=True)
    enable_notifications = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)

    # ------------------------------------------------------------
    # reCAPTCHA Configuration
    # ------------------------------------------------------------
    recaptcha_enabled = models.BooleanField(default=False)
    recaptcha_mode = models.CharField(
        max_length=20,
        choices=[("v2", "v2"), ("v3", "v3")],
        default="v2",
    )
    recaptcha_public_key = models.CharField(max_length=100, blank=True, null=True)
    recaptcha_private_key = models.CharField(max_length=100, blank=True, null=True)
    recaptcha_score_threshold = models.FloatField(default=0.5)
    recaptcha_timeout_ms = models.PositiveIntegerField(default=3000)

    # ------------------------------------------------------------
    # Device & MFA Policies
    # ------------------------------------------------------------
    max_devices_per_user = models.PositiveIntegerField(default=3)
    lock_duration_minutes = models.PositiveIntegerField(default=15)
    fingerprint_mode = models.CharField(
        max_length=20,
        choices=[("strict", "Strict"), ("lenient", "Lenient")],
        default="strict",
    )
    enforce_unique_device = models.BooleanField(default=True)
    require_mfa = models.BooleanField(default=False)
    mfa_totp_issuer = models.CharField(max_length=50, default="GsmInfinity")

    # ------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------
    email_verification_code_length = models.PositiveIntegerField(default=6)
    email_verification_code_type = models.CharField(
        max_length=20,
        choices=[("numeric", "Numeric"), ("alphanumeric", "Alphanumeric")],
        default="alphanumeric",
    )

    # ------------------------------------------------------------
    # Robustness & Rate Limiting
    # ------------------------------------------------------------
    max_login_attempts = models.PositiveIntegerField(default=5)
    rate_limit_window_seconds = models.PositiveIntegerField(default=300)
    cache_ttl_seconds = models.PositiveIntegerField(default=600)

    # ------------------------------------------------------------
    # Verification Resources
    # ------------------------------------------------------------
    meta_tags = models.ManyToManyField(
        "VerificationMetaTag", blank=True, related_name="site_settings_meta"
    )
    verification_files = models.ManyToManyField(
        "VerificationFile", blank=True, related_name="site_settings_files"
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.site_name

    # ------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------
    def get_theme(self):
        """Return dict of theme configuration for templates."""
        return {
            "theme_profile": self.theme_profile,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "ai_mode": self.ai_theme_mode,
        }

    def recaptcha_config(self):
        """Return configuration dict for frontend injection."""
        return {
            "enabled": self.recaptcha_enabled,
            "mode": self.recaptcha_mode,
            "public_key": self.recaptcha_public_key,
        }


# ============================================================
#  META TAG VERIFICATION
# ============================================================
class VerificationMetaTag(models.Model):
    """
    Stores meta tag verification data for services (Google, Bing, etc.).
    Used for SEO or ownership validation.
    """
    provider = models.CharField(max_length=50, db_index=True)
    name_attr = models.CharField(max_length=100)
    content_attr = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["provider", "name_attr"])]
        verbose_name = "Verification Meta Tag"
        verbose_name_plural = "Verification Meta Tags"

    def __str__(self):
        return f"{self.provider}: {self.name_attr}"


# ============================================================
#  FILE-BASED VERIFICATION
# ============================================================
class VerificationFile(models.Model):
    """
    Stores verification files for domain ownership (e.g., Google Search Console).
    """
    provider = models.CharField(max_length=50, db_index=True)
    file = models.FileField(upload_to="verification/")
    description = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [models.Index(fields=["provider"])]
        verbose_name = "Verification File"
        verbose_name_plural = "Verification Files"

    def __str__(self):
        return f"{self.provider}: {self.file.name}"


# ============================================================
#  TENANT-SPECIFIC SETTINGS
# ============================================================
class TenantSiteSettings(models.Model):
    """
    Per-site configuration for multi-tenant deployments.
    Overrides global color themes and verification metadata.
    """
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name="tenant_settings")
    theme_profile = models.CharField(max_length=50, blank=True, null=True)
    primary_color = models.CharField(max_length=20, blank=True, null=True)
    secondary_color = models.CharField(max_length=20, blank=True, null=True)
    meta_tags = models.ManyToManyField(VerificationMetaTag, blank=True)
    verification_files = models.ManyToManyField(VerificationFile, blank=True)

    class Meta:
        verbose_name = "Tenant Site Settings"
        verbose_name_plural = "Tenant Site Settings"

    def __str__(self):
        return f"Settings for {self.site.domain}"

    def get_colors(self):
        """Return color configuration for this tenant."""
        return {
            "primary": self.primary_color or "#007bff",
            "secondary": self.secondary_color or "#6c757d",
        }
