from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.ai_behavior.models import BehaviorInsight


def record_insight(
    *,
    related_user=None,
    device_identifier: str | None = None,
    related_ip: str | None = None,
    severity: str = "low",
    recommendation: str = "",
    metadata: dict[str, Any] | None = None,
) -> BehaviorInsight:
    """
    Minimal ingestion point for risk/anomaly insights.
    """
    return BehaviorInsight.objects.create(
        related_user=related_user,
        device_identifier=device_identifier,
        related_ip=related_ip,
        severity=severity,
        recommendation=recommendation,
        metadata=metadata or {},
        created_at=timezone.now(),
    )


def promote_from_device_event(event: dict[str, Any]) -> BehaviorInsight | None:
    """
    Lightweight heuristic: flag blocked or repeated failures as high severity.
    """
    try:
        severity = "low"
        recommendation = "Monitor device activity."
        if event.get("reason") in {"blocked_device", "policy_violation"}:
            severity = "high"
            recommendation = "Block or review device."
        elif not event.get("success"):
            severity = "medium"
            recommendation = "Ask for MFA on next login."

        return record_insight(
            related_user=event.get("user"),
            device_identifier=event.get("device_identifier"),
            related_ip=event.get("ip"),
            severity=severity,
            recommendation=recommendation,
            metadata=event,
        )
    except Exception:
        return None


__all__ = ["record_insight", "promote_from_device_event"]
