
# apps/users/models.py
"""
apps/users/models.py

GSMInfinity - authoritative, enterprise-grade user models.

Design:
- CustomUser (email primary)
- Notification & Announcement models
- Defensive DB operations and logging
- Compatible with Django 5.2+ / Python 3.12
"""

from __future__ import annotations

import logging
import re
import secrets
import string
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from solo.models import SingletonModel

logger = logging.getLogger(__name__)

_PHONE_NORMALIZE_RE = re.compile(r"[^\d+]")  # keep digits and leading +


# --------------------------------------------------------------------------
# User manager
# --------------------------------------------------------------------------
class CustomUserManager(BaseUserManager):
    """Custom manager with unified user/superuser creation."""

    use_in_migrations = True

    def _create_user(
        self,
        email: str,
        username: Optional[str],
        password: Optional[str],
        **extra_fields: Any,
    ) -> "CustomUser":
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).strip().lower()
        username = (username or email.split("@")[0]).strip()[:150]

        with transaction.atomic():
            user = self.model(email=email, username=username, **extra_fields)
            if password:
                user.set_password(password)
            else:
                user.set_unusable_password()
            user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> "CustomUser":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> "CustomUser":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not (extra_fields.get("is_staff") and extra_fields.get("is_superuser")):
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, username, password, **extra_fields)


# --------------------------------------------------------------------------
# CustomUser
# --------------------------------------------------------------------------
class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Core authentication model with verification & tracking.
    Email is the primary unique identifier.
    """

    # Identity
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(
        max_length=150, unique=True, null=True, blank=True, db_index=True
    )
    username_changes_this_year = models.PositiveIntegerField(default=0)
    username_last_changed_at = models.DateTimeField(null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True, default="")

    # Profile
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        AUTHOR = "author", "Author"
        MODERATOR = "moderator", "Moderator"
        READER = "reader", "Reader"

    role = models.CharField(max_length=50, null=True, blank=True, choices=Roles.choices)

    # Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Credits (referrals deprecated)
    credits = models.PositiveIntegerField(default=0)
    referral_code = models.CharField(
        max_length=12,
        unique=False,
        blank=True,
        null=True,
        db_index=True,
        help_text="Referral system disabled by default; code is optional.",
    )
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )

    # Security & verification
    unlock_count = models.PositiveIntegerField(default=0)
    last_unlock = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    verification_code = models.CharField(max_length=24, blank=True)

    # Signup metadata
    signup_method = models.CharField(
        max_length=20,
        choices=[("manual", "Manual"), ("social", "Social")],
        default="manual",
    )
    manual_signup = models.BooleanField(default=False)
    profile_completed = models.BooleanField(
        default=False,
        help_text="Indicates whether the user has completed their onboarding/profile setup.",
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    # Manager / ID
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # keep empty to simplify superuser creation prompts
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
        return self.email or (self.username or f"user-{self.pk}")

    # ============================================================
    # Minimal model clean / normalization
    # ============================================================
    def clean(self) -> None:
        # Normalize email and phone before validations
        if self.email:
            self.email = str(self.email).strip().lower()
        if self.phone:
            normalized = _PHONE_NORMALIZE_RE.sub("", str(self.phone))
            self.phone = normalized

    def save(self, *args, **kwargs) -> None:
        """
        Persist user with normalization. Referral codes are deprecated and no longer auto-assigned.
        """
        try:
            self.clean()
        except Exception:
            logger.debug("cleanup failed in save(); proceeding with save")

        if not self.pk:
            if not self.username and self.email:
                base = self.email.split("@")[0][:120]
                slug = slugify(base) or f"user{secrets.token_hex(3)}"
                if CustomUser.objects.filter(username=slug).exists():
                    slug = f"{slug[:10]}{secrets.token_hex(2)}"
                self.username = slug
            super().save(*args, **kwargs)

        try:
            super().save(*args, **kwargs)
        except Exception as exc:
            logger.exception("Failed to save user %s : %s", getattr(self, "email", None), exc)
            raise

    # ============================================================
    # Utilities
    # ============================================================
    @property
    def is_verified(self) -> bool:
        return bool(self.email_verified_at)

    def has_role(self, *roles: str) -> bool:
        if not self.role:
            return False
        return self.role in roles

    def is_admin(self) -> bool:
        return self.is_superuser or self.has_role(self.Roles.ADMIN)

    def is_editor(self) -> bool:
        return self.has_role(self.Roles.EDITOR)

    def is_author(self) -> bool:
        return self.has_role(self.Roles.AUTHOR)

    def is_moderator(self) -> bool:
        return self.has_role(self.Roles.MODERATOR)

    def mark_email_verified(self) -> None:
        if not self.email_verified_at:
            self.email_verified_at = timezone.now()
            try:
                self.save(update_fields=["email_verified_at"])
            except Exception as exc:
                logger.exception("Email verification update failed: %s", exc)

    def generate_verification_code(
        self, length: int | None = None, code_type: str | None = None
    ) -> str:
        """
        Generate and persist an email verification code.

        Defaults to a 6-character hexadecimal code (0-9, A-F).
        Falls back to SiteSettings for length/type when available.
        """
        if length is None or length <= 0:
            try:
                from apps.site_settings.models import SiteSettings

                ss = SiteSettings.get_solo()
                length = int(getattr(ss, "email_verification_code_length", 6) or 6)
            except Exception:
                length = 6
        if code_type is None:
            try:
                from apps.site_settings.models import SiteSettings

                ss = SiteSettings.get_solo()
                code_type = getattr(ss, "email_verification_code_type", "hex")
            except Exception:
                code_type = "hex"

        length = max(1, min(int(length), 24))

        ctype = str(code_type).lower()
        if ctype == "numeric":
            alphabet = string.digits
        elif ctype in {"hex", "hexadecimal"}:
            alphabet = string.digits + "ABCDEF"
        else:
            alphabet = string.ascii_uppercase + string.digits

        code = "".join(secrets.choice(alphabet) for _ in range(length))
        self.verification_code = code
        try:
            self.save(update_fields=["verification_code"])
        except Exception as exc:
            logger.exception("Verification code save failed for %s : %s", self.email, exc)
        return code

    def increment_unlock(self) -> None:
        try:
            self.unlock_count = (self.unlock_count or 0) + 1
            self.last_unlock = timezone.now()
            self.save(update_fields=["unlock_count", "last_unlock"])
        except Exception as exc:
            logger.exception("Unlock counter update failed: %s", exc)

    def add_credits(self, amount: int) -> None:
        if amount > 0:
            try:
                self.credits = (self.credits or 0) + int(amount)
                self.save(update_fields=["credits"])
            except Exception as exc:
                logger.exception("Credit update failed: %s", exc)



# --------------------------------------------------------------------------
# Notification
# --------------------------------------------------------------------------
class Notification(models.Model):
    """Multi-channel user notifications with audit timestamps."""

    PRIORITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]
    CHANNEL_CHOICES = [
        ("web", "Web"),
        ("email", "Email"),
        ("sms", "SMS"),
        ("push", "Push"),
    ]

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
            models.Index(
                fields=["recipient", "is_read"], name="notif_recipient_read_idx"
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} → {getattr(self.recipient, 'email', 'unknown')}"

    def mark_as_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            try:
                self.save(update_fields=["is_read", "read_at"])
            except Exception as exc:
                logger.exception("Failed to mark notification read: %s", exc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.pk,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "channel": self.channel,
            "is_read": bool(self.is_read),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }

    def to_json(self) -> Dict[str, Any]:
        return self.to_dict()

    def author_schema(self) -> Dict[str, Any]:
        """Basic author schema info for SEO."""
        return {
            "@type": "Person",
            "name": self.full_name or self.username or self.email,
            "url": getattr(self, "profile_url", None) or "",
        }


# --------------------------------------------------------------------------
# Announcement
# --------------------------------------------------------------------------
class Announcement(models.Model):
    """Global or segmented announcements for users or staff."""

    AUDIENCE_CHOICES = [
        ("all", "All"),
        ("user", "Users"),
        ("staff", "Staff"),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default="all")
    is_global = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
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
            models.Index(
                fields=["is_global", "start_at"], name="announce_global_start_idx"
            )
        ]

    def __str__(self) -> str:
        return self.title

    def active_now(self) -> bool:
        now = timezone.now()
        if self.start_at and self.start_at > now:
            return False
        if self.expires_at and self.expires_at <= now:
            return False
        return bool(self.is_global or self.audience)

    def deactivate_if_expired(self) -> None:
        if self.expires_at and self.expires_at < timezone.now() and self.is_global:
            self.is_global = False
            try:
                self.save(update_fields=["is_global"])
            except Exception as exc:
                logger.exception("Failed to deactivate expired announcement: %s", exc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.pk,
            "title": self.title,
            "message": self.message,
            "audience": self.audience,
            "is_global": bool(self.is_global),
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": getattr(self.created_by, "email", None)
            or getattr(self.created_by, "username", None)
            or None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_json(self) -> Dict[str, Any]:
        return self.to_dict()


# --------------------------------------------------------------------------
# UsersSettings (app-local, singleton)
# --------------------------------------------------------------------------
class UsersSettings(SingletonModel):
    """
    Per-project settings for the Users app.

    Kept independent so the app can be dropped into other projects
    without relying on a monolithic SiteSettings model.
    """

    enable_signup = models.BooleanField(default=True)
    enable_password_reset = models.BooleanField(default=True)
    enable_notifications = models.BooleanField(default=True)

    require_mfa = models.BooleanField(default=False)
    mfa_totp_issuer = models.CharField(max_length=50, default="Site")

    max_login_attempts = models.PositiveIntegerField(default=5)
    rate_limit_window_seconds = models.PositiveIntegerField(default=300)

    enable_payments = models.BooleanField(default=True)
    required_profile_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of user model fields that should trigger a profile-completion prompt.",
    )

    class Meta:
        verbose_name = "Users Settings"

    def __str__(self) -> str:
        return "Users Settings"


