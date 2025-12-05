from __future__ import annotations

import logging
from typing import Dict

from django.db import DatabaseError

from .models import SecurityConfig

logger = logging.getLogger(__name__)


def get_security_config():
    try:
        return SecurityConfig.get_solo()
    except DatabaseError:
        return None
    except Exception as exc:  # pragma: no cover - defensive path
        logger.debug("SecurityConfig unavailable: %s", exc)
        return None


def security_settings_snapshot() -> Dict[str, object]:
    cfg = get_security_config()
    if not cfg:
        return {}
    return {
        "DEVICES_ENABLED": cfg.devices_enabled,
        "BOTS_ENABLED": cfg.crawler_guard_enabled,
        "RISK_ENABLED": cfg.login_risk_enabled,
        "DEFAULT_LOGIN_RISK_POLICY": cfg.login_risk_policy,
        "DEVICE_QUOTA_ENFORCEMENT_ENABLED": cfg.device_quota_enforcement_enabled,
        "DEFAULT_DEVICE_WINDOW": cfg.default_device_window,
        "DEFAULT_DEVICE_LIMIT": cfg.default_device_limit,
        "CRAWLER_DEFAULT_ACTION": cfg.crawler_default_action,
        "MFA_POLICY": cfg.mfa_policy,
        "SECURITY_TIER": cfg.security_tier,
    }


def get_device_quota_policy() -> Dict[str, object]:
    cfg = get_security_config()
    if not cfg or not cfg.device_quota_enforcement_enabled:
        return {"enforcement_enabled": False}
    window_map = {"3m": 90, "6m": 180, "12m": 365}
    return {
        "enforcement_enabled": True,
        "default_window": cfg.default_device_window,
        "default_limit": int(cfg.default_device_limit or 5),
        "window_days": window_map.get(cfg.default_device_window, 365),
    }
