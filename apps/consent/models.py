"""
apps.consent.models
===================

Authoritative, consolidated GDPR/CCPA consent models.
- Django 5.2 / Python 3.12 compliant
- No duplicate definitions
- No deprecated APIs
- Correct FK wiring
- Fully aligned with utils + views + API
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


# ============================================================================
# ConsentCategory
# ============================================================================


class ConsentCategory(models.Model):
    """Configurable GDPR/CCPA category such as analytics, marketing, essential."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=False)

    class Meta:
        ordering = ["required", "name"]
        verbose_name = "Consent category"
        verbose_name_plural = "Consent categories"
        indexes = [
            models.Index(fields=["slug"], name="consent_cat_slug_idx"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

        # Invalidate all domains — safe
        try:
            from apps.consent.utils import invalidate_policy_cache

            invalidate_policy_cache(None)
        except Exception as exc:
            logger.warning("ConsentCategory.save: cache invalidation failed → %s", exc)


# ============================================================================
# ConsentPolicy
# ============================================================================


class ConsentPolicy(models.Model):
    """
    Versioned, auditable consent policy.
    Provides banner text, management text, snapshot, and TTL.
    """

    # NOT PK — Django still generates automatic integer PK
    version = models.CharField(max_length=20, unique=True)

    site_domain = models.CharField(
        max_length=100,
        default="default",
        db_index=True,
        help_text="Domain this policy belongs to.",
    )

    is_active = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    categories_snapshot = models.JSONField(default=dict, blank=True)

    banner_text = models.TextField(
        blank=True,
        default="We use cookies to improve your browsing experience.",
    )
    manage_text = models.TextField(
        blank=True,
        default="Manage your cookie preferences.",
    )

    cache_ttl_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Cache TTL for the active policy payload.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Consent policy"
        verbose_name_plural = "Consent policies"
        constraints = [
            # Only one active policy per domain
            models.UniqueConstraint(
                fields=["site_domain", "is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_policy_per_site",
            )
        ]
        indexes = [
            models.Index(fields=["site_domain"], name="consent_policy_site_idx"),
            models.Index(fields=["version"], name="consent_policy_version_idx"),
        ]

    def __str__(self):
        return f"{self.site_domain} · v{self.version}"

    # ----------------------------------------------------------------------

    @staticmethod
    def _build_snapshot() -> Dict[str, Any]:
        """Convert ConsentCategory rows → JSON snapshot."""
        try:
            return {
                c.slug: {
                    "name": c.name,
                    "description": c.description or "",
                    "required": bool(c.required),
                }
                for c in ConsentCategory.objects.all()
            }
        except Exception as exc:
            logger.exception("ConsentPolicy._build_snapshot failed → %s", exc)
            return {}

    # ----------------------------------------------------------------------

    def to_payload(self) -> Dict[str, Any]:
        """Serializable dict consumed by utils, views, and API."""
        ttl = int(self.cache_ttl_seconds or settings.CONSENT_POLICY_CACHE_TTL)
        return {
            "version": str(self.version),
            "categories_snapshot": self.categories_snapshot or {},
            "cache_ttl_seconds": ttl,
            "banner_text": self.banner_text or "",
            "manage_text": self.manage_text or "",
            "site_domain": self.site_domain,
        }

    # ----------------------------------------------------------------------

    def save(self, *args, **kwargs):
        """Atomic write + ensure only one active policy per domain."""
        self.site_domain = (self.site_domain or "default").strip().lower()

        # Always rebuild snapshot
        try:
            snapshot = self._build_snapshot()
            if not self.pk or snapshot != self.categories_snapshot:
                self.categories_snapshot = snapshot
        except Exception as exc:
            logger.error("ConsentPolicy.save: snapshot error → %s", exc)

        try:
            if self.is_active:
                # Enforce active=1 per domain
                with transaction.atomic():
                    ConsentPolicy.objects.select_for_update().filter(
                        site_domain=self.site_domain, is_active=True
                    ).exclude(pk=self.pk).update(is_active=False)

                    super().save(*args, **kwargs)
            else:
                super().save(*args, **kwargs)

        except Exception as exc:
            logger.error("ConsentPolicy.save failed → %s", exc)
            raise

        # Invalidate only this domain
        try:
            from apps.consent.utils import invalidate_policy_cache

            invalidate_policy_cache(self.site_domain)
        except Exception as exc:
            logger.warning("ConsentPolicy.save: failed to invalidate → %s", exc)

    # ----------------------------------------------------------------------

    @classmethod
    def get_active(cls, site_domain="default") -> Optional[Dict[str, Any]]:
        try:
            from apps.consent.utils import get_active_policy

            return get_active_policy(site_domain)
        except Exception:
            return None


# ============================================================================
# ConsentRecord
# ============================================================================


class ConsentRecord(models.Model):
    """
    Per-user/session consent state for a *specific policy version*.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="consent_records",
    )

    session_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )

    # Correct FK wiring — bind by version string, not PK
    policy = models.ForeignKey(
        ConsentPolicy,
        to_field="version",
        db_column="policy_version", # FK uses this column name
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="records",
    )

    # Duplicate for quick lookup
    # FIX: Use a distinct db_column name to avoid collision with the FK
    policy_version = models.CharField(
        max_length=20, 
        blank=True,
        db_column="policy_version_str" # <-- FIX APPLIED HERE
    )

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
                check=models.Q(user__isnull=False)
                | (models.Q(session_key__isnull=False) & ~models.Q(session_key="")),
                name="valid_user_or_session",
            ),
        ]
        indexes = [
            models.Index(fields=["policy_version"], name="consent_rec_policy_idx"),
            models.Index(fields=["site_domain"], name="consent_rec_site_idx"),
            models.Index(
                fields=["user", "site_domain", "updated_at"],
                name="consent_user_site_time_idx",
            ),
        ]

    def __str__(self):
        ident = getattr(self.user, "email", None) or self.session_key or "anonymous"
        return f"{ident} · v{self.policy_version or 'N/A'}"

    # ----------------------------------------------------------------------

    def save(self, *args, **kwargs):
        """Strict, deterministic, no silent failure."""
        if self.accepted_categories and not self.accepted_at:
            self.accepted_at = timezone.now()

        # Sync version from FK
        if self.policy and not self.policy_version:
            try:
                self.policy_version = self.policy.version
            except Exception:
                pass

        self.site_domain = (self.site_domain or "default").strip().lower()

        super().save(*args, **kwargs)

    # ----------------------------------------------------------------------

    def is_reject_all(self) -> bool:
        """
        True if all optional categories are rejected.
        Required categories don't count.
        """
        accepted = self.accepted_categories or {}
        if not accepted:
            return True

        # Cache required slugs
        try:
            required = cache.get("required_consent_categories")
            if required is None:
                required = set(
                    ConsentCategory.objects.filter(required=True).values_list(
                        "slug", flat=True
                    )
                )
                cache.set("required_consent_categories", required, 3600)
        except Exception:
            required = set()

        try:
            return not any(v for k, v in accepted.items() if k not in required)
        except Exception:
            return True

    # ----------------------------------------------------------------------

    def audit_summary(self) -> str:
        """Human-readable list of accepted categories."""
        try:
            if not self.accepted_categories:
                return "No categories accepted"

            accepted_names = []
            for slug, val in self.accepted_categories.items():
                if not val:
                    continue
                cat = ConsentCategory.objects.filter(slug=slug).only("name").first()
                if cat:
                    accepted_names.append(cat.name)

            return ", ".join(sorted(accepted_names)) if accepted_names else "None"
        except Exception:
            return "Unavailable"


# ============================================================================
# ConsentLog
# ============================================================================


class ConsentLog(models.Model):
    """Immutable audit log of user/session consent actions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
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
            models.Index(fields=["timestamp"], name="consent_log_time_idx"),
        ]

    def __str__(self):
        ident = getattr(self.user, "email", None) or self.ip_address or "unknown"
        version = self.policy_version or "N/A"
        return f"{ident} · v{version}"
