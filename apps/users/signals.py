"""
apps.users.signals
-------------------
Centralized user-related signal handlers for GSMInfinity.

✅ Handles:
- user_logged_in → register device fingerprint, enforce per-user limits.
- user_signed_up → mark new users for profile completion (social signup flow).

✅ Fully compatible with:
  Django 5.x / allauth ≥ 0.65
  apps.users.utils.device
  apps.site_settings.models.SiteSettings
"""

import logging
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from allauth.account.signals import user_signed_up

from apps.users.utils.device import register_fingerprint, enforce_device_limit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  User Logged In → Register or update device fingerprint
# ---------------------------------------------------------------------------
@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    """
    Triggered whenever a user logs in successfully (standard or social login).

    Responsibilities:
    - Capture and register the current device fingerprint.
    - Enforce per-user device limits from SiteSettings.
    - Skip registration gracefully if limit exceeded (strict mode).
    """
    try:
        if not request:
            logger.warning("handle_user_logged_in called without request.")
            return

        # Collect fingerprint info from request headers/cookies
        fingerprint_data = {
            "fingerprint_hash": (
                request.META.get("DEVICE_FP")
                or request.COOKIES.get("device_fp")
                or request.META.get("HTTP_USER_AGENT", "unknown")
            )[:255],
            "os_info": request.META.get("OS_INFO", "")[:100],
            "browser_info": request.META.get("HTTP_USER_AGENT", "")[:255],
            "motherboard_id": request.META.get("MOTHERBOARD_ID", "")[:100],
        }

        # Enforce per-user device limit
        if not enforce_device_limit(user):
            logger.warning(
                "User %s exceeded device limit (strict mode). Fingerprint not recorded.",
                getattr(user, "email", user.pk),
            )
            return

        # Register or update the fingerprint record
        register_fingerprint(
            user=user,
            fingerprint_hash=fingerprint_data["fingerprint_hash"],
            os_info=fingerprint_data["os_info"],
            motherboard_id=fingerprint_data["motherboard_id"],
            browser_info=fingerprint_data["browser_info"],
        )
        logger.info(
            "Device fingerprint recorded for user %s",
            getattr(user, "email", user.pk),
        )

    except Exception as exc:
        logger.exception("Error registering fingerprint for user %s: %s", user.pk, exc)


# ---------------------------------------------------------------------------
#  User Signed Up → Flag for onboarding/profile completion
# ---------------------------------------------------------------------------
@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """
    Triggered after a new user (social or email signup) is created.
    Ensures social signups enter onboarding (“Tell us about you”) flow.
    """
    try:
        if hasattr(user, "needs_profile_completion"):
            user.needs_profile_completion = True
            user.save(update_fields=["needs_profile_completion"])
            logger.debug(
                "User %s flagged for onboarding/profile completion",
                getattr(user, "email", user.pk),
            )
        else:
            logger.debug(
                "User model has no 'needs_profile_completion' field; skipping flag.",
            )
    except Exception as exc:
        logger.exception(
            "Error post-processing signup for user %s: %s",
            getattr(user, "email", user.pk),
            exc,
        )
