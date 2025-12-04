
"""
Public API surface for AI Behavior Engine (loaded via AppService).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from apps.ai_behavior.models import BehaviorInsight
from apps.ai_behavior.services import record_insight, promote_from_device_event

__all__ = ["record_insight", "promote_from_device_event", "BehaviorInsight"]


