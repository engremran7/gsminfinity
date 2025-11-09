"""
apps.consent.signals
---------------------
Enterprise-grade signal handlers for consent management.

✅ Features:
- Seamless merge of session → user consent on login
- Cleans up redundant session records post-merge
- Safe handling of site resolution and session keys
- Automatic cleanup on logout
"""

import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.sites.shortcuts import get_current_site

from .models import ConsentRecord, ConsentPolicy

logger = logging.getLogger(__name__)


# ============================================================
#  USER LOGIN — Merge Consent from Session
# ============================================================
@receiver(user_logged_in)
def merge_session_consent(sender, user, request, **kwargs):
    """
    On user login, merge any session-based consent record
    into the user's permanent consent record.
    """

    try:
        site_domain = get_current_site(request).domain
    except Exception:
        site_domain = getattr(request, "get_host", lambda: "default")()

    try:
        policy = (
            ConsentPolicy.objects.filter(site_domain=site_domain, is_active=True)
            .order_by("-created_at")
            .first()
        )
        if not policy:
            logger.debug("merge_session_consent: no active policy for site %s", site_domain)
            return

        session_key = getattr(request.session, "session_key", None)
        if not session_key:
            logger.debug("merge_session_consent: session missing for %s", user)
            return

        session_rec = ConsentRecord.objects.filter(
            session_key=session_key,
            policy_version=policy.version,
            site_domain=site_domain,
        ).first()

        if not session_rec:
            return

        user_rec, created = ConsentRecord.objects.get_or_create(
            user=user,
            policy_version=policy.version,
            site_domain=site_domain,
            defaults={
                "accepted_categories": session_rec.accepted_categories,
                "session_key": session_key,
            },
        )

        if not created:
            user_rec.accepted_categories = session_rec.accepted_categories
            user_rec.save(update_fields=["accepted_categories", "updated_at"])
            logger.debug(
                "merge_session_consent: updated existing user consent for %s → %s",
                user.email,
                site_domain,
            )
        else:
            logger.debug(
                "merge_session_consent: created new consent record for %s → %s",
                user.email,
                site_domain,
            )

        # ✅ cleanup session record after successful merge
        session_rec.delete()
        logger.debug("merge_session_consent: cleaned up session record for %s", session_key)

    except Exception as exc:
        logger.exception("merge_session_consent: failed for %s → %s", user, exc)


# ============================================================
#  USER LOGOUT — Clear Session Consent
# ============================================================
@receiver(user_logged_out)
def clear_session_consent(sender, request, user, **kwargs):
    """
    On logout, clean up transient consent data from session to
    prevent stale consent persistence or accidental reuse.
    """

    try:
        if hasattr(request, "session"):
            request.session.pop("consent_data", None)
            logger.debug("clear_session_consent: cleared session consent for %s", user)
    except Exception as exc:
        logger.debug("clear_session_consent: failed to clear session data → %s", exc)
