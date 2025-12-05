
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from apps.consent.utils import check as consent_check
from apps.core.app_service import AppService
from apps.core.utils.ip import get_client_ip
from apps.devices.models import AppPolicy, Device, DeviceConfig, DeviceEvent
from apps.devices.models_quota import UserDeviceQuota

logger = logging.getLogger(__name__)

Policy = Dict[str, Any]
Identity = Dict[str, Any]


def _hash_server_fingerprint(ua: str, ip: str, session_key: str) -> str:
    payload = f"{ua}|{ip}|{session_key}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_effective_policy(request, user=None, service_name: str | None = None) -> Policy:
    """
    Combine global DeviceConfig + AppPolicy into an effective policy snapshot.
    """
    config = DeviceConfig.get_solo()
    app_name = getattr(settings, "DEVICE_APP_NAME", "default")
    try:
        app_policy = AppPolicy.objects.get(name=app_name)
    except AppPolicy.DoesNotExist:
        app_policy = None

    policy: Policy = {
        "basic_fp": bool(getattr(config, "basic_fingerprinting_enabled", True)),
        "enhanced_fp": bool(getattr(config, "enhanced_fingerprinting_enabled", False)),
        "device_locking_mode": "none",
        "mfa_requirement": "none",
        "ai_risk_scoring": bool(getattr(config, "ai_risk_scoring_enabled", False)),
        "max_devices": int(getattr(config, "max_devices_default", 5) or 5),
        "monthly_quota": getattr(config, "monthly_device_quota", None),
        "yearly_quota": getattr(config, "yearly_device_quota", None),
        "ad_unlock_enabled": bool(getattr(config, "ad_unlock_enabled", False)),
        "strict_new_device_login": bool(getattr(config, "strict_new_device_login", False)),
        "require_mfa_on_new_device": bool(getattr(config, "require_mfa_on_new_device", False)),
        "allow_server_fallback": bool(getattr(config, "allow_server_fallback", True)),
        "device_expiry_days": getattr(config, "device_expiry_days", None),
        "service_rules": {},
    }

    if app_policy:
        policy.update(
            {
                "basic_fp": policy["basic_fp"] and app_policy.basic_fingerprinting,
                "enhanced_fp": policy["enhanced_fp"] and app_policy.enhanced_fingerprinting,
                "device_locking_mode": app_policy.device_locking_mode or policy["device_locking_mode"],
                "mfa_requirement": app_policy.mfa_requirement or policy["mfa_requirement"],
                "ai_risk_scoring": policy["ai_risk_scoring"] or app_policy.ai_risk_scoring,
                "service_rules": app_policy.service_level_rules or {},
                "monthly_quota": app_policy.monthly_device_quota or policy["monthly_quota"],
                "yearly_quota": app_policy.yearly_device_quota or policy["yearly_quota"],
                "ad_unlock_enabled": app_policy.ad_unlock_enabled or policy["ad_unlock_enabled"],
            }
        )

    if service_name:
        svc_rules = policy["service_rules"].get(service_name, {})
        if isinstance(svc_rules, dict):
            policy["service_rules"] = svc_rules
        else:
            policy["service_rules"] = {}
    return policy


def resolve_identity(
    request,
    user=None,
    service_name: str | None = None,
) -> Identity:
    """
    Resolve device identity using primary (machine_uuid), secondary (enhanced FP),
    or tertiary (server fallback) methods. Returns a dict with identity details.
    """
    policy = get_effective_policy(request, user=user, service_name=service_name)
    consent = getattr(request, "consent_categories", {}) or {}
    ip = get_client_ip(request) or ""
    ua = (request.META.get("HTTP_USER_AGENT") or "").strip()

    machine_uuid = (
        request.META.get("HTTP_X_DEVICE_ID")
        or request.POST.get("machine_uuid")
        or request.GET.get("machine_uuid")
        or request.COOKIES.get("machine_uuid")
        or None
    )

    fingerprint_hash = request.META.get("HTTP_X_DEVICE_FINGERPRINT") or request.POST.get("fingerprint_hash")
    fingerprint_blob_raw = request.POST.get("fingerprint_blob") or request.META.get("HTTP_X_DEVICE_FP_BLOB")
    fingerprint_blob = None
    if fingerprint_blob_raw:
        try:
            if len(fingerprint_blob_raw.encode("utf-8")) <= 16384:
                candidate = json.loads(fingerprint_blob_raw)
                fingerprint_blob = candidate if isinstance(candidate, dict) else None
        except Exception:
            fingerprint_blob = None

    enhanced_allowed = bool(policy.get("enhanced_fp")) and bool(
        consent_check("fraud_prevention", request) or consent.get("fraud_prevention")
    )

    identity_level = "none"
    server_fallback_fp = None

    if machine_uuid:
        identity_level = "primary"
    elif policy.get("allow_server_fallback", True):
        # Minimal consent for security: allow fallback unless explicitly denied
        session_key = getattr(getattr(request, "session", None), "session_key", "") or ""
        server_fallback_fp = _hash_server_fingerprint(ua, ip, session_key)
        identity_level = "fallback"

    return {
        "machine_uuid": machine_uuid,
        "fingerprint_hash": fingerprint_hash if enhanced_allowed else None,
        "fingerprint_blob": fingerprint_blob if enhanced_allowed else None,
        "server_fallback_fp": server_fallback_fp,
        "identity_level": identity_level,
        "policy_snapshot": policy,
        "consent_snapshot": consent,
        "ip": ip,
        "user_agent": ua,
    }


def resolve_or_create_device(
    request,
    user,
    service_name: str | None = None,
) -> Tuple[Optional[Device], bool, Dict[str, Any]]:
    """
    Resolve an existing device or create a new one subject to policy rules.
    Returns (device, is_new, context).
    """
    ident = resolve_identity(request, user=user, service_name=service_name)
    policy = ident["policy_snapshot"]
    now = timezone.now()

    device = None
    is_new = False

    if ident["machine_uuid"]:
        device = Device.objects.filter(user=user, machine_uuid=ident["machine_uuid"]).first()
    elif ident["server_fallback_fp"]:
        device = Device.objects.filter(user=user, machine_uuid=ident["server_fallback_fp"]).first()

    # Expire stale devices if configured
    expiry_days = policy.get("device_expiry_days")
    if expiry_days:
        cutoff = now - timezone.timedelta(days=int(expiry_days))
        Device.objects.filter(user=user, last_seen_at__lt=cutoff).delete()

    if device:
        device.last_seen_at = now
        if ident["fingerprint_hash"]:
            device.fingerprint_hash = ident["fingerprint_hash"]
        if ident["fingerprint_blob"]:
            device.metadata = ident["fingerprint_blob"]
        device.save(update_fields=["last_seen_at", "fingerprint_hash", "metadata"])
    else:
        # Enforce monthly/yearly quotas before creating
        monthly_quota = policy.get("monthly_quota")
        yearly_quota = policy.get("yearly_quota")
        override = UserDeviceQuota.objects.filter(user=user).first()

        if monthly_quota:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_count = Device.objects.filter(user=user, first_seen_at__gte=month_start).count()
            if month_count >= int(monthly_quota):
                return None, False, {"reason": "monthly_device_quota", "policy": policy}
        if yearly_quota:
            year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            year_count = Device.objects.filter(user=user, first_seen_at__gte=year_start).count()
            if year_count >= int(yearly_quota):
                return None, False, {"reason": "yearly_device_quota", "policy": policy}

        # Enforce user-specific rolling window quota if configured
        if override:
            window_map = {"3m": 90, "6m": 180, "12m": 365}
            days = window_map.get(override.window, 180)
            window_start = max(override.last_reset_at, now - timezone.timedelta(days=days))
            registrations = Device.objects.filter(user=user, first_seen_at__gte=window_start).count()
            limit = override.max_devices if override.max_devices is not None else policy.get("max_devices") or 5
            if registrations >= int(limit):
                _emit_security_event(
                    "device_quota_exceeded",
                    user=user,
                    device=None,
                    ip=ident.get("ip"),
                    metadata={"window_days": days, "limit": limit},
                )
                return None, False, {"reason": "user_window_quota", "policy": policy, "window_days": days}

        # Enforce global rolling quota when enabled in SecurityConfig (only if no per-user override)
        if not override:
            try:
                from apps.security_suite.api import get_device_quota_policy

                quota_policy = get_device_quota_policy()
            except Exception:
                quota_policy = {"enforcement_enabled": False}
            if quota_policy.get("enforcement_enabled"):
                window_days = int(quota_policy.get("window_days", 365))
                quota_record, _ = UserDeviceQuota.objects.get_or_create(
                    user=user,
                    defaults={
                        "window": quota_policy.get("default_window", "12m"),
                        "max_devices": None,
                        "last_reset_at": now,
                    },
                )
                window_start = max(quota_record.last_reset_at, now - timezone.timedelta(days=window_days))
                registrations = Device.objects.filter(user=user, first_seen_at__gte=window_start).count()
                limit = quota_policy.get("default_limit", policy.get("max_devices") or 5)
                if registrations >= int(limit):
                    _emit_security_event(
                        "device_quota_exceeded",
                        user=user,
                        device=None,
                        ip=ident.get("ip"),
                        metadata={"window_days": window_days, "limit": limit},
                    )
                    return None, False, {"reason": "device_quota_exceeded", "policy": policy, "window_days": window_days}

        # Enforce max devices (global + per-user override)
        max_devices = int((override.max_devices if override and override.max_devices is not None else policy.get("max_devices") or 5))
        current_count = Device.objects.filter(user=user).count()
        if current_count >= max_devices:
            if policy.get("device_locking_mode") == "strict":
                return None, False, {"reason": "limit_reached", "policy": policy}
            # soft mode: evict oldest
            oldest = Device.objects.filter(user=user).order_by("last_seen_at").first()
            if oldest:
                oldest.delete()
        device = Device.objects.create(
            user=user,
            machine_uuid=ident["machine_uuid"] or ident["server_fallback_fp"] or str(uuid.uuid4()),
            fingerprint_hash=ident["fingerprint_hash"] or "",
            metadata=ident["fingerprint_blob"] or {},
            first_seen_at=now,
            last_seen_at=now,
            is_trusted=not policy.get("strict_new_device_login", False),
        )
        is_new = True

    ident["is_new"] = is_new
    return device, is_new, ident


def enforce_device_policy_for_login(request, user) -> Tuple[bool, Dict[str, Any]]:
    """
    Enforce device policy during login.
    """
    device, is_new, ctx = resolve_or_create_device(request, user, service_name="login")

    if device and device.is_blocked:
        _log_event(device, user, "login", success=False, reason="blocked_device", ctx=ctx)
        return False, {"reason": "blocked_device", "device": device}

    policy = ctx["policy_snapshot"]

    if policy.get("strict_new_device_login") and is_new and not device.is_trusted:
        _log_event(device, user, "login", success=False, reason="untrusted_new_device", ctx=ctx)
        return False, {"reason": "untrusted_new_device", "device": device}

    if policy.get("require_mfa_on_new_device") and is_new:
        _log_event(device, user, "login", success=False, reason="mfa_required", ctx=ctx)
        return False, {"reason": "mfa_required", "device": device}

    _log_event(device, user, "login", success=True, reason="policy_pass", ctx=ctx)
    return True, {"device": device, "is_new": is_new, "context": ctx}


def enforce_device_policy_for_service(
    request,
    user,
    service_name: str,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Enforce device policy for a named service.
    """
    device, is_new, ctx = resolve_or_create_device(request, user, service_name=service_name)
    policy = ctx["policy_snapshot"]
    service_rules = policy.get("service_rules") or {}

    if device and device.is_blocked:
        _log_event(device, user, service_name, success=False, reason="blocked_device", ctx=ctx)
        return False, {"reason": "blocked_device", "device": device}

    if service_rules.get("trusted_device_only") and not (device and device.is_trusted):
        _log_event(device, user, service_name, success=False, reason="untrusted_device", ctx=ctx)
        return False, {"reason": "untrusted_device", "device": device}

    max_devices = service_rules.get("max_devices")
    if max_devices:
        count = Device.objects.filter(user=user).count()
        if count > int(max_devices):
            _log_event(device, user, service_name, success=False, reason="service_device_limit", ctx=ctx)
            return False, {"reason": "service_device_limit", "device": device}

    _log_event(device, user, service_name, success=True, reason="policy_pass", ctx=ctx)
    return True, {"device": device, "is_new": is_new, "context": ctx}


def _log_event(device: Optional[Device], user, event_type: str, success: bool, reason: str, ctx: dict) -> None:
    payload = {
        "device": device,
        "user": user if getattr(user, "is_authenticated", False) else None,
        "event_type": event_type,
        "success": success,
        "reason": reason,
        "ip": ctx.get("ip", ""),
        "user_agent": ctx.get("user_agent", ""),
        "metadata": {"policy": ctx.get("policy_snapshot"), "consent": ctx.get("consent_snapshot")},
    }
    try:
        evt = DeviceEvent.objects.create(**payload)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning(
            "Failed to persist DeviceEvent; continuing without event",
            exc_info=True,
            extra={"device_id": getattr(device, "id", None), "event_type": event_type},
        )
        return
    _emit_security_event(
        f"device_{event_type}",
        user=payload.get("user"),
        device=device,
        ip=payload.get("ip"),
        metadata={"success": success, "reason": reason, "policy": ctx.get("policy_snapshot", {})},
    )

    # Notify user when a new device registers successfully
    try:
        if success and payload["user"] and ctx.get("is_new"):
            from apps.users.services.notifications import send_notification

            send_notification(
                payload["user"],
                "New device registered",
                f"A new device ({getattr(device, 'machine_uuid', 'unknown')}) was added from {payload.get('ip') or 'unknown IP'}.",
                level="warning",
                channel="web",
            )
    except Exception:
        pass

    # Forward to AI behavior engine if available
    try:
        ai_api = AppService.get("ai_behavior")
        if ai_api and hasattr(ai_api, "promote_from_device_event"):
            ai_api.promote_from_device_event(
                {
                    "device_identifier": getattr(device, "machine_uuid", None),
                    "ip": payload["ip"],
                    "user": payload["user"],
                    "event_type": event_type,
                    "success": success,
                    "reason": reason,
                    "metadata": payload.get("metadata", {}),
                }
            )
    except Exception:
        pass


def _emit_security_event(event_type: str, user=None, device=None, ip: str | None = None, metadata: dict | None = None):
    try:
        from apps.security_events.api import emit_security_event

        emit_security_event(event_type, user=user, device=device, ip=ip, metadata=metadata)
    except Exception:
        return
