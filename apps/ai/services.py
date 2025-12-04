
from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from apps.ai.models import AISettings, KnowledgeSource, ModelEndpoint, PipelineRun, Workflow

logger = logging.getLogger(__name__)


def get_settings() -> Dict[str, Any]:
    try:
        s = AISettings.get_solo()
        return {
            "ai_enabled": s.ai_enabled,
            "default_model": s.default_model,
            "vector_search": s.enable_vector_search,
            "auto_translation": s.enable_auto_translation,
            "safety_firewall": s.enable_safety_firewall,
            "default_locale": s.default_locale,
        }
    except Exception as exc:
        # Fail closed: if settings cannot be loaded, keep features off.
        logger.error("AI settings fallback (fail closed): %s", exc)
        return {
            "ai_enabled": False,
            "default_model": None,
            "vector_search": False,
            "auto_translation": False,
            "safety_firewall": False,
            "default_locale": "en",
        }


def run_workflow(workflow_name: str, payload: Dict[str, Any], user=None) -> PipelineRun:
    wf = Workflow.objects.filter(name=workflow_name, is_active=True).first()
    requester = user if getattr(user, "is_authenticated", False) else None

    if wf is None:
        # Explicit failed run when workflow is missing/disabled.
        return PipelineRun.objects.create(
            workflow=None,
            requested_by=requester,
            input_payload=payload or {},
            status="failed",
            output_payload={"error": "Workflow not found or inactive", "requested": workflow_name},
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    run = PipelineRun.objects.create(
        workflow=wf,
        requested_by=requester,
        input_payload=payload or {},
        status="running",
        started_at=timezone.now(),
    )
    # TODO: delegate to async worker; here we just store stub output
    run.output_payload = {"message": "Execution delegated", "inputs": payload}
    run.status = "succeeded"
    run.finished_at = timezone.now()
    run.save(update_fields=["output_payload", "status", "finished_at"])
    return run


def register_knowledge_source(name: str, source_type: str, location: str, metadata: Optional[Dict[str, Any]] = None) -> KnowledgeSource:
    return KnowledgeSource.objects.create(
        name=name,
        source_type=source_type,
        location=location,
        metadata=metadata or {},
    )


def list_models(kind: str | None = None) -> Dict[str, Any]:
    qs = ModelEndpoint.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    return {
        "models": [
            {"name": m.name, "kind": m.kind, "provider": m.provider, "endpoint": m.endpoint}
            for m in qs
        ]
    }


__all__ = ["get_settings", "run_workflow", "register_knowledge_source", "list_models"]


