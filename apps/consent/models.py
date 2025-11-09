"""
apps.consent.models
-------------------
Enterprise-grade GDPR / CCPA consent tracking and audit system.
"""

from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache


# ============================================================
#  Consent Category
# ============================================================
class ConsentCategory(models.Model):
    """Defines a named category of cookies or data usage."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Consent category"
        verbose_name_plural = "Consent categories"
        indexes = [
            models.Index(fields=["slug"], name="consent_cat_slug_idx")
        ]

    def __str__(self):
        return self.name


# ============================================================
#  Consent Policy
# ============================================================
class ConsentPolicy(models.Model):
    """Represents a versioned, auditable consent policy."""

    version = models.CharField(max_length=20, unique=True)  # ✅ must be unique
    site_domain = models.CharField(max_length=100, default="default", db_index=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    categories_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["site_domain", "is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_policy_per_site",
            ),
        ]
        indexes = [
            models.Index(fields=["site_domain"], name="consent_policy_site_idx"),
            models.Index(fields=["version"], name="consent_policy_version_idx"),
        ]
        verbose_name = "Consent policy"
        verbose_name_plural = "Consent policies"

    def __str__(self):
        return f"{self.site_domain} · v{self.version}"

    def save(self, *args, **kwargs):
        """Refresh category snapshot and enforce single active policy per site."""
        snapshot = {
            c.slug: {
                "name": c.name,
                "required": c.required,
                "description": c.description,
            }
            for c in ConsentCategory.objects.all()
        }

        if not self.pk or self.categories_snapshot != snapshot:
            self.categories_snapshot = snapshot

        if self.is_active:
            cache_key = f"active_consent_policy_{self.site_domain}"
            cache.delete(cache_key)
            with transaction.atomic():
                ConsentPolicy.objects.select_for_update().filter(
                    site_domain=self.site_domain
                ).exclude(pk=self.pk).update(is_active=False)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


# ============================================================
#  Consent Record
# ============================================================
class ConsentRecord(models.Model):
    """Stores user/session consent decisions for a given policy."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consent_records",
    )
    session_key = models.CharField(max_length=64, db_index=True, blank=True, null=True)

    policy = models.ForeignKey(
        "ConsentPolicy",
        to_field="version",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="consent_records",
        help_text="Optional foreign key for audit traceability",
    )

    # ✅ Use a separate DB column to avoid collision
    policy_version = models.CharField(max_length=20, blank=True, db_column="policy_version_text")

    site_domain = models.CharField(max_length=100, default="default")
    accepted_categories = models.JSONField(default=dict, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Consent record"
        verbose_name_plural = "Consent records"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "policy_version", "site_domain"],
                name="unique_consent_per_user",
            ),
            models.UniqueConstraint(
                fields=["session_key", "policy_version", "site_domain"],
                name="unique_consent_per_session",
            ),
            models.CheckConstraint(
                check=~(
                    models.Q(user__isnull=True)
                    & models.Q(session_key__isnull=True)
                ),
                name="user_or_session_required",
            ),
        ]
        indexes = [
            models.Index(fields=["policy_version"], name="consent_rec_policy_idx"),
            models.Index(fields=["site_domain"], name="consent_rec_site_idx"),
        ]

    def __str__(self):
        ident = getattr(self.user, "email", None) or self.session_key or "anonymous"
        return f"{ident} · v{self.policy_version or 'N/A'}"

    def save(self, *args, **kwargs):
        """Auto-fill accepted_at and sync version from FK."""
        if self.accepted_categories and not self.accepted_at:
            self.accepted_at = timezone.now()
        if self.policy and not self.policy_version:
            self.policy_version = self.policy.version
        super().save(*args, **kwargs)

    def is_reject_all(self) -> bool:
        """Return True if all non-required categories were rejected."""
        if not self.accepted_categories:
            return True
        cache_key = "required_consent_categories"
        required = cache.get(cache_key)
        if required is None:
            required = set(
                ConsentCategory.objects.filter(required=True)
                .values_list("slug", flat=True)
            )
            cache.set(cache_key, required, timeout=3600)
        for slug, accepted in self.accepted_categories.items():
            if accepted and slug not in required:
                return False
        return True

    def audit_summary(self) -> str:
        """Readable summary of accepted categories."""
        if not self.accepted_categories:
            return "No categories accepted"
        accepted_names = [
            cat.name
            for slug, val in self.accepted_categories.items()
            if val and (cat := ConsentCategory.objects.filter(slug=slug).first())
        ]
        return ", ".join(accepted_names) if accepted_names else "None"


# ============================================================
#  Consent Log
# ============================================================
class ConsentLog(models.Model):
    """Audit trail for consent changes over time."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consent_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accepted_categories = models.JSONField(default=dict, blank=True)
    policy_version = models.CharField(max_length=20, blank=True)
    site_domain = models.CharField(max_length=100, default="default")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Consent log"
        verbose_name_plural = "Consent logs"
        indexes = [
            models.Index(fields=["timestamp"], name="consent_log_time_idx")
        ]

    def __str__(self):
        user_display = (
            getattr(self.user, "email", None)
            or self.ip_address
            or "unknown"
        )
        return f"{user_display} @ {self.timestamp:%Y-%m-%d %H:%M}"
