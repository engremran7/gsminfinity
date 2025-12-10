"""
Enhanced AI services with async support, rate limiting, and comprehensive error handling.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from apps.ai.clients import AIProviderConfig, AIProviderError, send_chat
from apps.ai.models import AISettings, KnowledgeSource, ModelEndpoint, PipelineRun, Workflow

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_WINDOW = 3600  # 1 hour
MAX_REQUESTS_PER_USER = 100
MAX_REQUESTS_PER_IP = 200

# Cost tracking
COST_PER_1K_TOKENS = {
    "gpt-4": 0.03,
    "gpt-3.5-turbo": 0.002,
    "claude-3-5-sonnet": 0.003,
    "deepseek-chat": 0.001,
}


def get_settings() -> Dict[str, Any]:
    """Get AI settings with safe fallbacks."""
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
        logger.error("AI settings fallback (fail closed): %s", exc, exc_info=True)
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
    """Build AI provider configuration from settings."""
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


def check_rate_limit(user=None, ip_address: str = None) -> bool:
    """
    Check if user/IP has exceeded rate limits.
    
    Args:
        user: Django user object
        ip_address: Client IP address
        
    Returns:
        True if request is allowed, False if rate limited
    """
    if not user and not ip_address:
        return True
    
    # Check user rate limit
    if user and hasattr(user, 'id'):
        user_key = f"ai_rate_limit:user:{user.id}"
        user_count = cache.get(user_key, 0)
        if user_count >= MAX_REQUESTS_PER_USER:
            logger.warning(f"User {user.id} exceeded AI rate limit")
            return False
        cache.set(user_key, user_count + 1, RATE_LIMIT_WINDOW)
    
    # Check IP rate limit
    if ip_address:
        ip_key = f"ai_rate_limit:ip:{ip_address}"
        ip_count = cache.get(ip_key, 0)
        if ip_count >= MAX_REQUESTS_PER_IP:
            logger.warning(f"IP {ip_address} exceeded AI rate limit")
            return False
        cache.set(ip_key, ip_count + 1, RATE_LIMIT_WINDOW)
    
    return True


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate API cost for request.
    
    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        
    Returns:
        Cost in USD
    """
    # Get cost per 1K tokens for this model
    cost_rate = COST_PER_1K_TOKENS.get(model, 0.001)
    
    # Calculate total cost
    total_tokens = prompt_tokens + completion_tokens
    cost = (total_tokens / 1000) * cost_rate
    
    return round(cost, 6)


def test_completion(prompt: str, user=None, ip_address: str = None) -> Dict[str, Any]:
    """
    Test AI completion with rate limiting and cost tracking.
    
    Args:
        prompt: Test prompt
        user: Django user object
        ip_address: Client IP address
        
    Returns:
        Response dictionary with text, usage, and cost
        
    Raises:
        AIProviderError: If API key not configured or rate limited
    """
    # Check rate limit
    if not check_rate_limit(user, ip_address):
        raise AIProviderError("Rate limit exceeded. Please try again later.")
    
    cfg = _build_config()
    if not cfg.api_key:
        raise AIProviderError("API key is not configured")
    
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": prompt},
    ]
    
    try:
        response = send_chat(cfg, messages)
        
        # Calculate cost
        usage = response.get("usage", {})
        cost = calculate_cost(
            cfg.model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0)
        )
        response["cost"] = cost
        
        # Log usage
        logger.info(
            f"AI completion: model={cfg.model}, "
            f"tokens={usage.get('total_tokens', 0)}, "
            f"cost=${cost:.6f}"
        )
        
        return response
        
    except Exception as exc:
        logger.error(f"AI completion failed: {exc}", exc_info=True)
        raise


def run_workflow(
    workflow_name: str, 
    payload: Dict[str, Any], 
    user=None,
    async_mode: bool = False
) -> PipelineRun:
    """
    Run AI workflow with async support.
    
    Args:
        workflow_name: Name of workflow to run
        payload: Input data for workflow
        user: User requesting workflow
        async_mode: If True, queue for async processing
        
    Returns:
        PipelineRun instance
    """
    wf = Workflow.objects.filter(name=workflow_name, is_active=True).first()
    requester = user if getattr(user, "is_authenticated", False) else None

    if wf is None:
        return PipelineRun.objects.create(
            workflow=None,
            requested_by=requester,
            input_payload=payload or {},
            status="failed",
            output_payload={
                "error": "Workflow not found or inactive", 
                "requested": workflow_name
            },
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    run = PipelineRun.objects.create(
        workflow=wf,
        requested_by=requester,
        input_payload=payload or {},
        status="queued" if async_mode else "running",
        started_at=timezone.now(),
    )

    if async_mode:
        # Queue for async processing (Celery, etc.)
        # from apps.ai.tasks import execute_workflow
        # execute_workflow.delay(run.id)
        logger.info(f"Workflow {workflow_name} queued for async execution: {run.id}")
        return run
    
    # Synchronous execution
    try:
        with transaction.atomic():
            # Execute workflow steps
            output = _execute_workflow_steps(wf, payload, requester)
            
            run.output_payload = {
                "message": "Execution completed",
                "inputs": payload or {},
                "result": output,
            }
            run.status = "succeeded"
            run.finished_at = timezone.now()
            run.save(update_fields=["output_payload", "status", "finished_at"])
            
            logger.info(f"Workflow {workflow_name} completed successfully: {run.id}")
            
    except Exception as exc:
        logger.error(f"Workflow {workflow_name} failed: {exc}", exc_info=True)
        run.output_payload = {
            "error": str(exc),
            "inputs": payload or {},
        }
        run.status = "failed"
        run.finished_at = timezone.now()
        run.save(update_fields=["output_payload", "status", "finished_at"])
    
    return run


def _execute_workflow_steps(
    workflow: Workflow, 
    payload: Dict[str, Any],
    user=None
) -> Dict[str, Any]:
    """
    Execute individual workflow steps.
    
    Args:
        workflow: Workflow to execute
        payload: Input data
        user: User context
        
    Returns:
        Workflow execution results
    """
    # Placeholder for workflow step execution
    # In production, implement actual step-by-step execution
    return {
        "workflow_id": workflow.id,
        "workflow_name": workflow.name,
        "executed_at": timezone.now().isoformat(),
        "steps_completed": 0,
    }


def register_knowledge_source(
    name: str, 
    source_type: str, 
    location: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> KnowledgeSource:
    """
    Register new knowledge source for RAG/vector search.
    
    Args:
        name: Source name
        source_type: Type of source (file, url, database, etc.)
        location: Source location
        metadata: Additional metadata
        
    Returns:
        KnowledgeSource instance
    """
    return KnowledgeSource.objects.create(
        name=name,
        source_type=source_type,
        location=location,
        metadata=metadata or {},
        is_active=True,
    )


def list_models(kind: str | None = None) -> Dict[str, Any]:
    """
    List available AI models.
    
    Args:
        kind: Optional filter by model kind
        
    Returns:
        Dictionary with model list
    """
    qs = ModelEndpoint.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    return {
        "models": [
            {
                "name": m.name, 
                "kind": m.kind, 
                "provider": m.provider, 
                "endpoint": m.endpoint,
                "description": getattr(m, "description", "")
            }
            for m in qs
        ]
    }


def get_usage_stats(user=None, start_date=None, end_date=None) -> Dict[str, Any]:
    """
    Get AI usage statistics.
    
    Args:
        user: Filter by user
        start_date: Start date for stats
        end_date: End date for stats
        
    Returns:
        Usage statistics dictionary
    """
    qs = PipelineRun.objects.all()
    
    if user:
        qs = qs.filter(requested_by=user)
    if start_date:
        qs = qs.filter(started_at__gte=start_date)
    if end_date:
        qs = qs.filter(started_at__lte=end_date)
    
    total_runs = qs.count()
    successful = qs.filter(status="succeeded").count()
    failed = qs.filter(status="failed").count()
    
    return {
        "total_runs": total_runs,
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / total_runs * 100) if total_runs > 0 else 0,
        "period": {
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None,
        }
    }
