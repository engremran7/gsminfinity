
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from django.utils import timezone
from django.conf import settings

from apps.ai.clients import AIProviderConfig, AIProviderError, send_chat
from apps.ai.models import AISettings, KnowledgeSource, ModelEndpoint, PipelineRun, Workflow

logger = logging.getLogger(__name__)


def get_settings() -> Dict[str, Any]:
    try:
        s = AISettings.get_solo()
        return {
            "ai_enabled": s.ai_enabled,
            "provider": s.provider,
            "base_url": s.base_url,
            "model": s.model_name,
            "default_model": s.default_model,
            "timeout_seconds": s.timeout_seconds,
            "max_tokens": s.max_tokens,
            "temperature": float(s.temperature),
            "log_prompts": s.log_prompts,
            "log_completions": s.log_completions,
            "pii_redaction": s.pii_redaction_enabled,
            "moderation_enabled": s.moderation_enabled,
            "allow_tools": s.allow_tools,
            "retry_limit": s.retry_limit,
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
            "provider": "deepseek",
            "base_url": "",
            "model": None,
            "default_model": None,
            "timeout_seconds": 30,
            "max_tokens": 1024,
            "temperature": 0.3,
            "log_prompts": False,
            "log_completions": False,
            "pii_redaction": True,
            "moderation_enabled": True,
            "allow_tools": False,
            "retry_limit": 3,
            "vector_search": False,
            "auto_translation": False,
            "safety_firewall": False,
            "default_locale": "en",
        }


def _build_config() -> AIProviderConfig:
    s = AISettings.get_solo()
    return AIProviderConfig(
        provider=s.provider or "deepseek",
        base_url=s.base_url or "",
        api_key=s.api_key or getattr(settings, "AI_API_KEY", ""),
        model=s.model_name or s.default_model or "deepseek-chat",
        timeout=s.timeout_seconds or 30,
        max_tokens=s.max_tokens or 1024,
        temperature=float(s.temperature or 0.3),
        allow_tools=s.allow_tools,
        log_prompts=s.log_prompts,
        log_completions=s.log_completions,
        pii_redaction=s.pii_redaction_enabled,
        moderation_enabled=s.moderation_enabled,
        retry_limit=s.retry_limit or 3,
        backoff_min_seconds=s.backoff_min_seconds or 0.5,
        backoff_max_seconds=s.backoff_max_seconds or 4.0,
    )


def test_completion(prompt: str) -> Dict[str, Any]:
    cfg = _build_config()
    if not cfg.api_key:
        raise AIProviderError("API key is not configured")
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": prompt},
    ]
    return send_chat(cfg, messages)


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
        status="queued",
        started_at=timezone.now(),
    )

    # Synchronous in-process execution placeholder.
    # If/when an async worker is wired in, this block becomes the enqueue step.
    run.output_payload = {
        "message": "Execution completed inline",
        "inputs": payload or {},
    }
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


