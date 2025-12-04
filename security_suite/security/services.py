"""
security_suite.security.services

Public facade for security concerns. All feature apps should call these helpers
instead of importing device/bot/risk modules directly. Each function degrades
gracefully when the optional subapps are not installed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from . import conf

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------
def get_device_id(request) -> Optional[str]:
    """Return a stable device identifier when security_devices is enabled; otherwise None."""
    if not conf.get("DEVICES_ENABLED", True):
        return None
    try:
        from security_suite.security_devices.services import get_or_create_device_id

        return get_or_create_device_id(request)
    except Exception as exc:
        logger.debug("security: device_id unavailable (%s)", exc)
        return None


def attach_device_to_user(request, user) -> None:
    """Associate current device with a user (no-op if unavailable)."""
    if not conf.get("DEVICES_ENABLED", True):
        return
    try:
        from security_suite.security_devices.services import attach_device_to_user as _attach

        _attach(request, user)
    except Exception as exc:
        logger.debug("security: attach_device_to_user skipped (%s)", exc)
        return


# ---------------------------------------------------------------------------
# Bots / crawler guard
# ---------------------------------------------------------------------------
def is_suspicious_bot(request) -> bool:
    """Return True if request appears to be a bot/crawler according to security_bots."""
    if not conf.get("BOTS_ENABLED", True):
        return False
    try:
        from security_suite.security_bots.services import is_suspicious

        return bool(is_suspicious(request))
    except Exception as exc:
        logger.debug("security: bot check unavailable (%s)", exc)
        return False


def classify_request(request) -> Dict[str, Any]:
    """Return a structured classification (or neutral defaults)."""
    if not conf.get("BOTS_ENABLED", True):
        return {"label": "unknown", "action": "allow"}
    try:
        from security_suite.security_bots.services import classify_request as _classify

        return _classify(request)
    except Exception as exc:
        logger.debug("security: classify_request unavailable (%s)", exc)
        return {"label": "unknown", "action": "allow"}


# ---------------------------------------------------------------------------
# Risk / AI behavior
# ---------------------------------------------------------------------------
def evaluate_login_risk(request, user=None) -> Dict[str, Any]:
    """
    Compute a risk assessment for a login attempt.
    Expected response shape:
        {"score": 0-100, "level": "none|low|medium|high", "reasons": [...]}
    """
    if not conf.get("RISK_ENABLED", True):
        return {"score": 0, "level": "none", "reasons": []}
    try:
        from security_suite.security_risk.services import get_current_risk

        return get_current_risk(request=request, user=user)
    except Exception as exc:
        logger.debug("security: login risk unavailable (%s)", exc)
        return {"score": 0, "level": "none", "reasons": []}


def record_security_event(event_type: str, request=None, user=None, metadata: Optional[Dict[str, Any]] = None):
    """Best-effort record of a security event (no-op if risk module absent)."""
    if not conf.get("RISK_ENABLED", True):
        return
    try:
        from security_suite.security_risk.services import record_event

        record_event(event_type=event_type, request=request, user=user, metadata=metadata)
    except Exception as exc:
        logger.debug("security: record_event skipped (%s)", exc)
        return


def should_require_additional_challenge(request, user=None, risk: Optional[Dict[str, Any]] = None) -> bool:
    """
    Decide whether to prompt for extra checks (e.g., MFA step-up) based on risk policy.
    """
    policy = conf.get("DEFAULT_LOGIN_RISK_POLICY", "mfa_if_high")
    risk_data = risk or evaluate_login_risk(request, user)
    level = str(risk_data.get("level", "none")).lower()
    if policy == "none":
        return False
    if policy == "info":
        return False
    if policy == "mfa_if_high":
        return level == "high"
    if policy == "block_if_high":
        return level in {"medium", "high"}
    return False
