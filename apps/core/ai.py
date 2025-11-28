from __future__ import annotations

import logging
import time
from typing import List, Dict, Any

from apps.core import ai_client
from apps.core.utils.logging import log_event

logger = logging.getLogger(__name__)


def generate_text(prompt: str, context: str = "", constraints: Dict[str, Any] | None = None, user=None) -> str:
    start = time.monotonic()
    full_prompt = prompt
    if context:
        full_prompt = f"{prompt}\nContext:\n{context}"
    try:
        result = ai_client.generate_answer(question=full_prompt, user=user)
        log_event(logger, "info", "ai.generate_text.success", elapsed_ms=round((time.monotonic() - start) * 1000))
        return result
    except Exception as exc:
        log_event(logger, "warning", "ai.generate_text.failed", error=str(exc))
        return ""


def classify_text(text: str, labels: List[str] | None = None, user=None) -> str:
    try:
        prompt = f"Classify the following text into one of the labels {labels}: {text}"
        result = ai_client.generate_answer(question=prompt, user=user)
        log_event(logger, "info", "ai.classify_text.success", labels=labels or [])
        return result
    except Exception as exc:
        log_event(logger, "warning", "ai.classify_text.failed", error=str(exc))
        return ""


def embed_text(text: str) -> bytes:
    try:
        # Placeholder: return empty bytes until embedding provider is wired.
        vec = b""
        log_event(logger, "info", "ai.embed_text.success", has_embedding=bool(vec))
        return vec
    except Exception as exc:
        log_event(logger, "warning", "ai.embed_text.failed", error=str(exc))
        return b""
