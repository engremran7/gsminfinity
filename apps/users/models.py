"""
apps.users.models

GSMInfinity Enterprise User Architecture
----------------------------------------
Enterprise-ready Django user system with:
- django-allauth integration
- MFA / device fingerprinting
- Notifications & announcements
- Referral / verification system
- AI personalization hooks (future-safe)

Key hardening applied:
- Atomic referral code generation with bounded attempts + fallback
- Clear indexes and constraints for frequent lookups
- Safe save/update semantics and small utility helpers
"""

from __future__ import annotations

import uuid
import random
import string
import logging
from typing import Optional

from django.db import models, transaction
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# Custom User Manager
# ------------------------------------------------------------
class CustomUserManager(BaseUserManager):
    """Custom manager providing unified create_user / create_superuser APIs."""

    use_in_migrations = True

    def create_user(self, email: str, username: Optional[str] = None, password: Optional[str] = None, **extra_fields) -> "CustomUser":
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        username = username or email.split("@")[0]

        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, username: Optional[str] = None, password: Optional[str] = None, **extra_fields) -> "CustomUser":
        """Create and return a superuser with elevated permissions."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self.create_user(email, username, password, **extra_fields)


# ------------------------------------------------------------
# Custom User Model
# ------------------------------------------------------------
class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Primary authentication model with referral, verification, and tracking."""

    # Identity
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, blank=True, null=True, db_index=True)
    full_name = models.CharField(max_length=150, default="No Name")

    # Profile
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)

    # Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Credits & referrals
    credits = models.PositiveIntegerField(default=0)
    referral_code = models.CharField(max_length=12, unique=True, blank=True, db_index=True)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )

    # Security & verification
    unlock_count = models.PositiveIntegerField(default=0)
    last_unlock = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_code = models.CharField(max_length=24, blank=True)

    # Signup meta
    signup_method = models.CharField(
        max_length=20,
        choices=[("manual", "Manual"), ("social", "Social")],
        default="manual",
    )
    needs_profile_completion = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "full_name"]

    objects = CustomUserManager()

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"], name="user_email_idx"),
            models.Index(fields=["username"], name="user_username_idx"),
            models.Index(fields=["referral_code"], name="user_referral_idx"),
        ]

    def __str__(self) -> str:
        return self.email or "Unnamed User"

    # ------------------------------------------------------------
    # Save override — robust referral code generation
    # ------------------------------------------------------------
    def _generate_referral_candidate(self) -> str:
        """Create a candidate code (human-friendly)."""
        # Mix of UUID + short randomness to reduce collisions
        return uuid.uuid4().hex[:8].upper()

    def save(self, *args, **kwargs) -> None:
        """
        Ensure referral_code is generated atomically and bounded to avoid infinite loops.
        Uses a short cache to reduce duplicate generation pressure under high concurrency.
        """
        if not self.referral_code:
            # Try to generate a unique code up to max_attempts
            max_attempts = 8
            attempts = 0
            generated = None

            while attempts < max_attempts:
                candidate = self._generate_referral_candidate()
                # Quick cache-level check to avoid DB hits under rush
                cache_key = f"refcode:{candidate}"
                if cache.get(cache_key):
                    attempts += 1
                    continue
                # Optimistic reserve in cache for a short window
                cache.set(cache_key, True, timeout=5)

                # Check DB under transaction to avoid race
                with transaction.atomic():
                    if not CustomUser.objects.filter(referral_code=candidate).exists():
                        generated = candidate
                        break
                # Not unique, try again
                cache.delete(cache_key)
                attempts += 1

            if not generated:
                # Fallback deterministic option using timestamp + random suffix
                suffix = random.randint(10000, 99999)
                generated = f"REF{int(timezone.now().timestamp()) % 100000}{suffix}"[:12].upper()

            self.referral_code = generated

        super().save(*args, **kwargs)

    # ------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------
    @property
    def is_verified(self) -> bool:
        """Return True if email is verified."""
        return bool(self.email_verified_at)

    def mark_email_verified(self) -> None:
        """Utility to mark email as verified."""
        if not self.email_verified_at:
            self.email_verified_at = timezone.now()
            self.save(update_fields=["email_verified_at"])

    def generate_verification_code(self, length: int = 6, code_type: str = "alphanumeric") -> str:
        """Generate and persist a verification code for email or MFA."""
        alphabet = string.digits if code_type == "numeric" else string.ascii_uppercase + string.digits
        code = "".join(random.choice(alphabet) for _ in range(length))
        self.verification_code = code
        # Persist only the verification_code field to avoid extra writes
        try:
            self.save(update_fields=["verification_code"])
        except Exception:
            # On rare failure, set in-memory and leave it (caller may retry)
            logger.exception("Failed to persist verification_code for user %s", self.email)
        return code

    def increment_unlock(self) -> None:
        """Increment the unlock_count and update last_unlock timestamp."""
        self.unlock_count = (self.unlock_count or 0) + 1
        self.last_unlock = timezone.now()
        self.save(update_fields=["unlock_count", "last_unlock"])

    def add_credits(self, amount: int) -> None:
        """Add credits safely (no negative additions)."""
        if amount <= 0:
            return
        self.credits = (self.credits or 0) + int(amount)
        self.save(update_fields=["credits"])


# ------------------------------------------------------------
# Device Fingerprint
# ------------------------------------------------------------
class DeviceFingerprint(models.Model):
    """Tracks device/browser identifiers for MFA and session trust."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fingerprint_hash = models.CharField(max_length=255)
    os_info = models.CharField(max_length=100, blank=True)
    motherboard_id = models.CharField(max_length=100, blank=True)
    browser_info = models.CharField(max_length=255, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "fingerprint_hash"], name="unique_user_fingerprint")
        ]
        ordering = ["-last_used_at"]
        verbose_name = "Device Fingerprint"
        verbose_name_plural = "Device Fingerprints"
        indexes = [
            models.Index(fields=["user", "is_active"], name="device_user_active_idx"),
        ]

    def __str__(self) -> str:
        # Defensive: user may be None during migrations/edge cases
        email = getattr(self.user, "email", "unknown")
        return f"{email} · {self.fingerprint_hash[:8]}"


# ------------------------------------------------------------
# Notification
# ------------------------------------------------------------
class Notification(models.Model):
    """Multi-channel user notifications with audit timestamps."""

    PRIORITY_CHOICES = [("info", "Info"), ("warning", "Warning"), ("critical", "Critical")]
    CHANNEL_CHOICES = [("web", "Web"), ("email", "Email"), ("sms", "SMS"), ("push", "Push")]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="info")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="web")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["recipient", "is_read"], name="notif_recipient_read_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title} → {getattr(self.recipient, 'email', 'unknown')}"

    def mark_as_read(self) -> None:
        """Mark the notification as read and record timestamp."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


# ------------------------------------------------------------
# Announcement
# ------------------------------------------------------------
class Announcement(models.Model):
    """Global or segmented announcements for users or staff."""

    AUDIENCE_CHOICES = [("all", "All"), ("user", "Users"), ("staff", "Staff")]

    title = models.CharField(max_length=255)
    message = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default="all")
    is_global = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_announcements",
    )
    start_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        indexes = [
            models.Index(fields=["is_global", "start_at"], name="announce_global_start_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_active(self) -> bool:
        """True if announcement is currently valid."""
        now = timezone.now()
        return self.start_at <= now and (not self.expires_at or self.expires_at > now)

    def deactivate_if_expired(self) -> None:
        """Deactivate announcement when expired (for CRON or Celery)."""
        if self.expires_at and self.expires_at < timezone.now() and self.is_global:
            self.is_global = False
            self.save(update_fields=["is_global"])
