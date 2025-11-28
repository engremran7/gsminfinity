"""
apps.consent.signals
====================

Enterprise-grade signal handlers for consent management.

✅ Django 5.2 / Python 3.12 Ready
✅ Seamless merge of session → user consent on login
✅ Cleans redundant session records post-merge
✅ Uses canonical utils for site & policy resolution
✅ Defensive session handling and cleanup
✅ Atomic DB ops, async-safe, no silent leaks
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from apps.consent.models import ConsentRecord
from apps.consent.utils import get_active_policy, resolve_site_domain
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db import transaction
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _safe_session_key(request) -> Optional[str]:
    """Return session key if available, else None."""
    try:
        return getattr(getattr(request, "session", None), "session_key", None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# USER LOGIN — Merge Session Consent
# ---------------------------------------------------------------------------


@receiver(user_logged_in, dispatch_uid="merge_session_consent_v2")
def merge_session_consent(sender: Any, user: Any, request, **kwargs) -> None:
    """
    On user login, merge any session-based consent record into the
    user's permanent consent record.

    - Uses canonical helpers
    - Fully defensive and idempotent
    - Atomic update to avoid partial merges
    """

    # 1️⃣ Resolve site domain
    try:
        site_domain = resolve_site_domain(request)
    except Exception as exc:
        logger.debug("merge_session_consent: resolve_site_domain failed → %s", exc)
        site_domain = "default"

    # 2️⃣ Retrieve active policy (payload dict)
    policy = get_active_policy(site_domain)
    if not policy:
        logger.debug("merge_session_consent: no active policy for site=%s", site_domain)
        return

    policy_version = str(policy.get("version", "") or "")
    if not policy_version:
        logger.debug(
            "merge_session_consent: active policy missing version for site=%s",
            site_domain,
        )
        return

    # 3️⃣ Get session key
    session_key = _safe_session_key(request)
    if not session_key:
        logger.debug(
            "merge_session_consent: session missing or no key for user=%s",
            getattr(user, "email", None),
        )
        return

    # 4️⃣ Fetch anonymous session consent record
    try:
        session_rec = ConsentRecord.objects.filter(
            session_key=session_key,
            policy_version=policy_version,
            site_domain=site_domain,
            user__isnull=True,
        ).first()
    except Exception as exc:
        logger.exception(
            "merge_session_consent: lookup failed for %s → %s", session_key, exc
        )
        return

    if not session_rec:
        logger.debug("merge_session_consent: no session record for key=%s", session_key)
        return

    # 5️⃣ Merge into user-level record (atomic)
    try:
        with transaction.atomic():
            user_rec, created = ConsentRecord.objects.select_for_update().get_or_create(
                user=user,
                policy_version=policy_version,
                site_domain=site_domain,
                defaults={
                    "accepted_categories": session_rec.accepted_categories,
                    "session_key": session_key,
                },
            )

            if created:
                logger.info(
                    "merge_session_consent: created consent v%s for %s (%s)",
                    policy_version,
                    getattr(user, "email", None),
                    site_domain,
                )
            else:
                if user_rec.accepted_categories != session_rec.accepted_categories:
                    user_rec.accepted_categories = session_rec.accepted_categories
                    user_rec.save(update_fields=["accepted_categories", "updated_at"])
                    logger.debug(
                        "merge_session_consent: updated existing consent for %s (site=%s)",
                        getattr(user, "email", None),
                        site_domain,
                    )

            # 6️⃣ Clean redundant session record
            try:
                session_rec.delete()
                logger.debug(
                    "merge_session_consent: cleaned session record key=%s", session_key
                )
            except Exception as exc:
                logger.debug(
                    "merge_session_consent: cleanup failed for %s → %s",
                    session_key,
                    exc,
                )

    except Exception as exc:
        logger.exception(
            "merge_session_consent: atomic merge failed for user=%s → %s",
            getattr(user, "email", None),
            exc,
        )


# ---------------------------------------------------------------------------
# USER LOGOUT — Clear Session Consent
# ---------------------------------------------------------------------------


@receiver(user_logged_out, dispatch_uid="clear_session_consent_v2")
def clear_session_consent(sender: Any, request, user: Any, **kwargs) -> None:
    """
    On logout, remove transient consent data from the session
    to prevent stale reuse in subsequent logins.
    """
    try:
        session = getattr(request, "session", None)
        if not session:
            logger.debug(
                "clear_session_consent: no session for user=%s",
                getattr(user, "email", None),
            )
            return

        if "consent_data" in session:
            session.pop("consent_data", None)
            try:
                session.save()
            except Exception as exc:
                logger.debug("clear_session_consent: session.save() failed → %s", exc)
            logger.debug(
                "clear_session_consent: cleared session consent for user=%s",
                getattr(user, "email", None),
            )

    except Exception as exc:
        logger.debug("clear_session_consent: unexpected failure → %s", exc)
