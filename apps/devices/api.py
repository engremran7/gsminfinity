
from __future__ import annotations

from typing import Any, Dict

from apps.devices.models import DeviceConfig
from apps.devices.services import (
    enforce_device_policy_for_login,
    enforce_device_policy_for_service,
    resolve_identity,
)


def get_settings() -> Dict[str, Any]:
    try:
        cfg = DeviceConfig.get_solo()
        return {
            "basic_fingerprinting_enabled": bool(cfg.basic_fingerprinting_enabled),
            "enhanced_fingerprinting_enabled": bool(cfg.enhanced_fingerprinting_enabled),
            "strict_new_device_login": bool(cfg.strict_new_device_login),
            "max_devices_default": int(cfg.max_devices_default or 5),
        }
    except Exception:
        return {
            "basic_fingerprinting_enabled": True,
            "enhanced_fingerprinting_enabled": False,
            "strict_new_device_login": False,
            "max_devices_default": 5,
        }


__all__ = [
    "get_settings",
    "enforce_device_policy_for_login",
    "enforce_device_policy_for_service",
    "resolve_identity",
]


