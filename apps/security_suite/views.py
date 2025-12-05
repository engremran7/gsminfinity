from __future__ import annotations

from typing import Any, Dict

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def security_status(request):
    """
    Lightweight status endpoint exposing active security modules and policies.
    Uses DB-backed SecurityConfig when available and AppRegistry flags for UI awareness.
    """
    payload: Dict[str, Any] = {"modules": {}, "policies": {}, "hints": {}}
    try:
        from apps.security_suite.api import security_settings_snapshot

        payload["policies"] = security_settings_snapshot()
    except Exception:
        payload["policies"] = {}

    try:
        from apps.core.models import AppRegistry

        reg = AppRegistry.get_solo()
        payload["modules"] = {
            "device_identity_enabled": getattr(reg, "device_identity_enabled", True),
            "crawler_guard_enabled": getattr(reg, "crawler_guard_enabled", True),
            "ai_behavior_enabled": getattr(reg, "ai_behavior_enabled", True),
        }
    except Exception:
        payload["modules"] = {}

    payload["hints"] = {
        "device_quota": "Enforces per-user rolling limit; override per user with UserDeviceQuota.",
        "crawler_guard": "Default action is controlled by SecurityConfig.crawler_default_action.",
        "login_risk": "Risk policy drives MFA step-up when login_risk_enabled is true.",
    }
    return JsonResponse(payload)
