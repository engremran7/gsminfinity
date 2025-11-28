"""
apps.users.signals
==================
Centralized user-related signal handlers for GSMInfinity.
"""

from __future__ import annotations

import logging

from allauth.account.signals import email_confirmed, user_signed_up
from allauth.account.utils import perform_login
from apps.users.utils.device import enforce_device_limit, register_fingerprint
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    if not user or not request:
        logger.debug("handle_user_logged_in: missing user or request context.")
        return

    try:
        fp_hash = (
            request.META.get("DEVICE_FP")
            or request.COOKIES.get("device_fp")
            or request.META.get("HTTP_USER_AGENT", "unknown")
        )[:255]

        fingerprint_data = {
            "fingerprint_hash": fp_hash,
            "os_info": (request.META.get("OS_INFO") or "").strip()[:100],
            "browser_info": (request.META.get("HTTP_USER_AGENT") or "").strip()[:255],
            "motherboard_id": (request.META.get("MOTHERBOARD_ID") or "").strip()[:100],
        }

        if not enforce_device_limit(user):
            logger.warning(
                "Device registration blocked - user %s exceeded device limit.",
                getattr(user, "email", user.pk),
            )
            return

        register_fingerprint(user=user, **fingerprint_data)
        logger.info(
            "Device fingerprint updated for user %s [%s]",
            getattr(user, "email", user.pk),
            fingerprint_data["fingerprint_hash"][:16],
        )

    except Exception as exc:
        logger.exception(
            "Error registering fingerprint for user %s: %s",
            getattr(user, "email", user.pk),
            exc,
        )


@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """
    Triggered immediately after a new user account is created
    (via email, social, or SSO signup).

    Responsibilities:
      • Set signup_method ("manual" | "social").
      • Ensure profile_completed=False so middleware can enforce onboarding.
      • Mark email_verified_at for social signups.
    """
    if not user:
        logger.debug("handle_user_signed_up: missing user instance.")
        return

    sociallogin = kwargs.get("sociallogin")
    is_social = bool(sociallogin)
    updated_fields: list[str] = []

    try:
        if hasattr(user, "signup_method"):
            desired_method = "social" if is_social else "manual"
            if getattr(user, "signup_method", None) != desired_method:
                user.signup_method = desired_method
                updated_fields.append("signup_method")

        if hasattr(user, "profile_completed"):
            if getattr(user, "profile_completed", True):
                user.profile_completed = False
                updated_fields.append("profile_completed")

        if is_social and hasattr(user, "email_verified_at"):
            if getattr(user, "email_verified_at", None) is None:
                user.email_verified_at = timezone.now()
                updated_fields.append("email_verified_at")

        if updated_fields:
            user.save(update_fields=updated_fields)
            logger.info(
                "User %s flagged for onboarding; updated fields=%s",
                getattr(user, "email", user.pk),
                updated_fields,
            )

        if sociallogin:
            try:
                perform_login(request, user, email_verification="optional")
            except Exception:
                pass

    except Exception as exc:
        logger.exception(
            "Error flagging signup completion for user %s: %s",
            getattr(user, "email", user.pk),
            exc,
        )

    # Register device fingerprint at signup if available
    try:
        fp_hash = (
            (request.POST.get("device_fp") if request else None)
            or (request.COOKIES.get("device_fp") if request else None)
            or (request.META.get("DEVICE_FP") if request else None)
            or (request.META.get("HTTP_USER_AGENT") if request else None)
            or "unknown"
        )[:255]

        fingerprint_data = {
            "fingerprint_hash": fp_hash,
            "os_info": (request.META.get("OS_INFO") if request else "" or "").strip()[:100],
            "browser_info": (request.META.get("HTTP_USER_AGENT") if request else "" or "").strip()[:255],
            "motherboard_id": (request.META.get("MOTHERBOARD_ID") if request else "" or "").strip()[:100],
        }

        if enforce_device_limit(user):
            register_fingerprint(user=user, **fingerprint_data)
    except Exception as exc:
        logger.debug("Signup fingerprint registration failed: %s", exc, exc_info=True)


@receiver(email_confirmed)
def handle_email_confirmed(request, email_address, **kwargs):
    """
    Sync allauth EmailAddress confirmations to CustomUser.email_verified_at.
    """
    try:
        user = getattr(email_address, "user", None)
        if not user:
            logger.debug("email_confirmed: missing user on email_address")
            return

        updated_fields = []
        if not getattr(user, "email_verified_at", None):
            user.email_verified_at = timezone.now()
            updated_fields.append("email_verified_at")

        if hasattr(user, "verification_code") and getattr(
            user, "verification_code", ""
        ):
            user.verification_code = ""
            updated_fields.append("verification_code")

        if updated_fields:
            user.save(update_fields=updated_fields)
            logger.info(
                "email_confirmed: marked verified for user=%s",
                getattr(user, "email", user.pk),
            )

        # Optional referral reward logic
        try:
            from django.conf import settings

            referrer_bonus = int(getattr(settings, "REFERRAL_REWARD_REFERRER", 0) or 0)
            new_user_bonus = int(getattr(settings, "REFERRAL_REWARD_NEW_USER", 0) or 0)

            if referrer_bonus > 0 and getattr(user, "referred_by", None):
                referrer = user.referred_by
                if hasattr(referrer, "add_credits"):
                    referrer.add_credits(referrer_bonus)
            if new_user_bonus > 0 and hasattr(user, "add_credits"):
                user.add_credits(new_user_bonus)
        except Exception as exc:
            logger.debug("Referral reward processing failed: %s", exc, exc_info=True)
    except Exception as exc:
        logger.exception("email_confirmed handler failed: %s", exc)
