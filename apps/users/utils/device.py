"""
apps.users.utils.device
-----------------------
Enterprise-grade device fingerprint and limit enforcement utilities for GSMInfinity.

✅ Features:
- Registers or updates DeviceFingerprint on each login.
- Enforces per-user device limits (strict / lenient) with ADMIN BYPASS.
- Thread-safe atomic updates, ORM-optimized (Django 5.x).
- Compatible with async-safe authentication and signals.
- Includes periodic admin cleanup utilities.
"""

import logging
from typing import Optional, Dict
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.users.models import DeviceFingerprint, CustomUser
from apps.site_settings.models import SiteSettings

logger = logging.getLogger(__name__)


# ============================================================
#  DEVICE REGISTRATION / UPDATE
# ============================================================
def register_fingerprint(
    user,
    fingerprint_hash: str,
    os_info: str = "",
    motherboard_id: str = "",
    browser_info: str = "",
) -> Optional[DeviceFingerprint]:
    """
    Create or update a DeviceFingerprint record for the given user.

    ADMIN USERS: Always allowed; fingerprint registered but no limit enforced.

    Returns:
        DeviceFingerprint | None
    """
    if not user or not fingerprint_hash:
        logger.warning("register_fingerprint: missing user or fingerprint_hash")
        return None

    try:
        with transaction.atomic():
            device, created = DeviceFingerprint.objects.select_for_update().get_or_create(
                user=user,
                fingerprint_hash=fingerprint_hash,
                defaults={
                    "os_info": os_info[:100],
                    "motherboard_id": motherboard_id[:100],
                    "browser_info": browser_info[:255],
                    "registered_at": timezone.now(),
                    "last_used_at": timezone.now(),
                    "is_active": True,
                },
            )

            update_fields = ["last_used_at"]
            device.last_used_at = timezone.now()

            # Update changed metadata only
            for field, value, limit in [
                ("os_info", os_info, 100),
                ("motherboard_id", motherboard_id, 100),
                ("browser_info", browser_info, 255),
            ]:
                truncated = (value or "")[:limit]
                if truncated and getattr(device, field) != truncated:
                    setattr(device, field, truncated)
                    update_fields.append(field)

            if not device.is_active:
                device.is_active = True
                update_fields.append("is_active")

            if update_fields:
                device.save(update_fields=update_fields)

        logger.debug(
            "DeviceFingerprint[%s] %s for %s (admin=%s) — fields: %s",
            device.pk,
            "created" if created else "updated",
            getattr(user, "email", user.pk),
            getattr(user, "is_staff", False),
            update_fields,
        )
        return device

    except Exception as exc:
        logger.exception("register_fingerprint failed for user=%s → %s", getattr(user, "pk", None), exc)
        return None


# ============================================================
#  DEVICE LIMIT ENFORCEMENT (ADMIN BYPASS)
# ============================================================
def enforce_device_limit(user) -> bool:
    """
    Enforces per-user device limits from SiteSettings.

    ✅ ADMIN BYPASS: Staff/superusers have unlimited devices.
    ✅ REGULAR USERS: Subject to device limit and eviction mode.

    Modes:
        - strict  → block new device registration if limit reached.
        - lenient → deactivate oldest fingerprints to make room.

    Returns:
        bool → True if allowed, False if blocked.
    """
    if not user:
        return True

    # ✅ Admin bypass
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        logger.debug("Device limit bypassed for admin user: %s", getattr(user, "email", user.pk))
        return True

    # Regular user enforcement
    try:
        settings_obj = SiteSettings.get_solo()
        limit = int(getattr(settings_obj, "max_devices_per_user", 3))
        mode = str(getattr(settings_obj, "fingerprint_mode", "strict")).lower()
    except Exception as exc:
        logger.warning("SiteSettings unavailable; using default device limit → %s", exc)
        limit, mode = 3, "strict"

    active_qs = (
        DeviceFingerprint.objects.filter(user=user, is_active=True)
        .only("id", "last_used_at")
        .order_by("last_used_at")
    )
    count = active_qs.count()

    if count < limit:
        logger.debug("User %s within limit (%d/%d)", getattr(user, "email", user.pk), count, limit)
        return True

    if mode == "lenient":
        to_remove = count - limit + 1
        logger.info(
            "Evicting %d oldest fingerprints for user %s (lenient mode)",
            to_remove,
            getattr(user, "email", user.pk),
        )
        try:
            with transaction.atomic():
                for fp in active_qs[:to_remove]:
                    fp.is_active = False
                    fp.save(update_fields=["is_active"])
            return True
        except Exception as exc:
            logger.error("Device eviction failed for %s → %s", getattr(user, "email", user.pk), exc)
            return False

    # strict mode block
    logger.warning(
        "Device registration BLOCKED for %s — limit reached (%d/%d, strict mode)",
        getattr(user, "email", user.pk),
        count,
        limit,
    )
    return False


# ============================================================
#  COMBINED SAFE HELPER (WITH ADMIN BYPASS)
# ============================================================
def record_device_fingerprint(
    request,
    user,
    fingerprint_data: Optional[Dict] = None,
) -> Optional[DeviceFingerprint]:
    """
    Unified helper for recording device fingerprints during login.

    ✅ ADMIN USERS: Always allowed (no enforcement)
    ✅ REGULAR USERS: Enforces per-user device limits

    Raises:
        PermissionError → strict mode violation for regular users
        ValidationError → missing fingerprint hash
    """
    fingerprint_data = fingerprint_data or {}

    # Determine fingerprint source
    fingerprint_hash = (
        fingerprint_data.get("fingerprint_hash")
        or getattr(request, "POST", {}).get("device_fp")
        or getattr(request, "COOKIES", {}).get("device_fp")
        or getattr(request, "META", {}).get("HTTP_USER_AGENT", "")
    )
    if not fingerprint_hash:
        raise ValidationError("record_device_fingerprint: missing fingerprint_hash")

    os_info = fingerprint_data.get("os_info") or request.META.get("HTTP_USER_AGENT", "")[:100]
    motherboard_id = fingerprint_data.get("motherboard_id", "")
    browser_info = fingerprint_data.get("browser_info") or request.META.get("HTTP_USER_AGENT", "")[:255]

    # ✅ Enforce device limit (with admin bypass)
    if not enforce_device_limit(user):
        raise PermissionError("Device registration blocked (strict mode limit reached)")

    device = register_fingerprint(
        user=user,
        fingerprint_hash=fingerprint_hash,
        os_info=os_info,
        motherboard_id=motherboard_id,
        browser_info=browser_info,
    )

    user_type = "admin" if (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)) else "user"
    logger.debug("record_device_fingerprint: device recorded for %s (%s)", getattr(user, "email", user.pk), user_type)
    return device


# ============================================================
#  ADMIN-SPECIFIC UTILITIES
# ============================================================
def get_admin_device_stats() -> Dict[str, Dict]:
    """
    Returns device statistics for admin users.
    Useful for dashboards, audits, or maintenance.
    """
    stats = {}
    for user in CustomUser.objects.filter(is_staff=True):
        devices = DeviceFingerprint.objects.filter(user=user, is_active=True)
        stats[user.email or f"User#{user.pk}"] = {
            "total_devices": devices.count(),
            "devices": list(
                devices.values("fingerprint_hash", "last_used_at", "os_info", "browser_info")
            ),
        }
    return stats


def cleanup_old_admin_devices(days_old: int = 30) -> int:
    """
    Clean up old admin device fingerprints.
    Admins have unlimited devices, so cleanup is routine maintenance.
    """
    cutoff_date = timezone.now() - timedelta(days=days_old)
    deleted_total = 0

    for user in CustomUser.objects.filter(is_staff=True):
        old_devices = DeviceFingerprint.objects.filter(user=user, last_used_at__lt=cutoff_date)
        count, _ = old_devices.delete()
        deleted_total += count
        if count:
            logger.info("Cleaned %d old devices for admin %s", count, user.email)

    logger.info("Total admin devices cleaned: %d", deleted_total)
    return deleted_total
