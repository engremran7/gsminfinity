"""
security_devices.services

Shim layer that currently delegates to the in-project devices app.
Eventually, the device models/logic should live inside this package.
"""

from __future__ import annotations

import logging
from typing import Optional

from . import conf

logger = logging.getLogger(__name__)


def get_or_create_device_id(request) -> Optional[str]:
    """Delegate to existing apps.devices for now; returns None on failure."""
    if not conf.get("PERSISTENCE_ENABLED", True):
        return None
    try:
        from apps.devices.services import get_or_create_machine_uuid  # type: ignore

        return get_or_create_machine_uuid(request)
    except Exception as exc:
        logger.debug("security_devices: device_id unavailable (%s)", exc)
        return None


def attach_device_to_user(request, user) -> None:
    """Associate device to user (best-effort shim to existing devices app)."""
    if not conf.get("ATTACH_ON_LOGIN", True):
        return
    try:
        from apps.devices.services import attach_device_to_user as _attach  # type: ignore

        _attach(request, user)
    except Exception as exc:
        logger.debug("security_devices: attach_device_to_user skipped (%s)", exc)
        return
