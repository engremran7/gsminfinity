"""
apps.users.signals
==================
Centralized user-related signal handlers for GSMInfinity.

✅ Handles:
    - user_logged_in → Register device fingerprint, enforce device limits.
    - user_signed_up → Flag user for onboarding after signup.

✅ Fully compatible with:
    Django ≥ 5.0, allauth ≥ 0.65, and GSMInfinity enterprise utils.

This module is designed to be import-safe (idempotent registration)
and non-blocking for async runtimes.
"""

from __future__ import annotations

import logging
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from allauth.account.signals import user_signed_up

from apps.users.utils.device import register_fingerprint, enforce_device_limit

logger = logging.getLogger(__name__)


# ============================================================
#  USER LOGGED IN  →  REGISTER DEVICE FINGERPRINT
# ============================================================

@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    """
    Triggered whenever a user logs in successfully (including social logins).

    Responsibilities:
      • Capture device fingerprint metadata from request headers or cookies.
      • Enforce per-user device limits (defined in SiteSettings).
      • Gracefully skip fingerprint creation when over limit (strict mode).
      • Never raise — logs exceptions but never disrupts login flow.
    """
    if not user or not request:
        logger.debug("handle_user_logged_in: missing user or request context.")
        return

    try:
        # --- Derive fingerprint fields (normalized length for DB safety)
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

        # --- Enforce per-user device limits
        if not enforce_device_limit(user):
            logger.warning(
                "Device registration blocked — user %s exceeded device limit.",
                getattr(user, "email", user.pk),
            )
            return

        # --- Register or update device record atomically
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


# ============================================================
#  USER SIGNED UP  →  PROFILE COMPLETION FLAG
# ============================================================

@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """
    Triggered immediately after a new user account is created
    (via email, social, or SSO signup).

    Responsibilities:
      • Flag user for onboarding / profile completion.
      • Maintain compatibility with custom user models (graceful skip).
    """
    if not user:
        logger.debug("handle_user_signed_up: missing user instance.")
        return

    try:
        if hasattr(user, "needs_profile_completion"):
            if not getattr(user, "needs_profile_completion", False):
                user.needs_profile_completion = True
                user.save(update_fields=["needs_profile_completion"])
                logger.debug(
                    "User %s flagged for onboarding.",
                    getattr(user, "email", user.pk),
                )
        else:
            logger.debug(
                "User model has no `needs_profile_completion` field; skipping onboarding flag."
            )

    except Exception as exc:
        logger.exception(
            "Error flagging signup completion for user %s: %s",
            getattr(user, "email", user.pk),
            exc,
        )
