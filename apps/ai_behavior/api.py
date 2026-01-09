"""
Public API surface for AI Behavior Engine (loaded via AppService).
"""

from __future__ import annotations

from apps.ai_behavior.models import BehaviorInsight
from apps.ai_behavior.services import promote_from_device_event, record_insight

__all__ = ["record_insight", "promote_from_device_event", "BehaviorInsight"]
