"""
apps.core.ai_client
-------------------
Enterprise AI provider integration for the assistant endpoint.

- OpenAI SDK v1-style implementation with timeouts
- Explicit configuration loading and fail-fast behaviour
- Safe fallbacks and structured logging
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional, List, Dict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

logger = logging.getLogger(__name__)
User = get_user_model()


class AiClientError(RuntimeError):
    """Raised when the AI backend cannot be used safely."""


@dataclass
class AiConfig:
    api_key: str
    model: str
    max_retries: int = 2
    retry_backoff: float = 0.75
    timeout: float = 15.0
    mock_mode: bool = False


def _load_config() -> AiConfig:
    """
    Load AI provider configuration from Django settings.
    """
    api_key = getattr(settings, "AI_OPENAI_API_KEY", "") or ""
    mock_mode = bool(getattr(settings, "AI_MOCK_MODE", False))

    if not api_key and not mock_mode:
        raise AiClientError("AI_OPENAI_API_KEY is not configured")

    model = getattr(settings, "AI_OPENAI_MODEL", "gpt-4.1-mini")
    timeout = float(getattr(settings, "AI_OPENAI_TIMEOUT", 15.0))
    max_retries = int(getattr(settings, "AI_OPENAI_MAX_RETRIES", 2))
    retry_backoff = float(getattr(settings, "AI_OPENAI_RETRY_BACKOFF", 0.75))

    return AiConfig(
        api_key=api_key,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        retry_backoff=retry_backoff,
        mock_mode=mock_mode,
    )


def _get_client(config: AiConfig):
    if OpenAI is None:
        raise AiClientError("OpenAI SDK is not installed")
    return OpenAI(api_key=config.api_key)


def _build_system_prompt(user: User) -> str:
    username = getattr(user, "username", "user")
    return (
        "You are the GSMInfinity support assistant. "
        "Answer questions concisely and accurately based on general knowledge. "
        "Never reveal internal system details, secrets, or source code. "
        f"User identifier: {username}."
    )


def generate_answer(*, question: str, user: User) -> str:
    """
    Main AI entrypoint used by apps.core.views.ai_assistant_view.

    Returns a plain text answer or raises AiClientError on config/client issues.
    """
    question = (question or "").strip()
    if not question:
        raise AiClientError("Empty question passed to generate_answer")

    config = _load_config()
    system_prompt = _build_system_prompt(user)

    start = time.monotonic()
    if config.mock_mode:
        return _mock_response(question)

    client = _get_client(config)

    attempts = config.max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            response = client.responses.create(
                model=config.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                timeout=config.timeout,
            )
            text = _extract_text_response(response)
            _emit_metrics(
                ok=bool(text),
                attempt=attempt,
                elapsed_ms=round((time.monotonic() - start) * 1000),
            )
            return text or "I don't have an answer for that yet."
        except Exception as exc:  # pragma: no cover - provider edge cases
            logger.warning(
                "AI provider attempt %s/%s failed: %s", attempt, attempts, exc
            )
            if attempt >= attempts:
                logger.exception("AI provider call failed after retries")
                raise AiClientError("AI provider call failed") from exc
            time.sleep(config.retry_backoff * attempt)

    return "I'm not sure how to answer that yet."


# --------------------------------------------------------------------
# Action-specific helpers (generate title/excerpt/seo/tags/summarize/moderate)
# If OpenAI is unavailable or not configured, fallback to simple heuristics.
# --------------------------------------------------------------------


def _fallback_title(text: str) -> str:
    base = text.strip() or "Concise, compelling title"
    return base[:120]


def _fallback_excerpt(text: str) -> str:
    return (text.strip() or "Add a short summary.").split(".")[0][:200]


def _fallback_tags(text: str) -> List[str]:
    seeds = ["ai", "engineering", "product", "update", "announcement", "guide"]
    out = []
    text_lower = text.lower()
    for t in seeds:
        if t in text_lower and t not in out:
            out.append(t)
    return out[:5] or ["general"]


def _fallback_seo(text: str) -> str:
    return (text.strip() or "Actionable, keyword-rich description for this post.")[:150]


def _fallback_summary(text: str) -> str:
    return "Summary: " + (text.strip()[:240] or "Key points and takeaways.")


def _fallback_moderation(text: str) -> Dict[str, str]:
    lower = text.lower()
    toxic = any(w in lower for w in ["hate", "kill", "idiot"])
    score = 0.8 if toxic else 0.05
    return {"toxicity_score": score, "label": "high" if toxic else "low"}


def _call_openai_response(config: AiConfig, system_prompt: str, user_content: str) -> str:
    start = time.monotonic()
    if config.mock_mode:
        return _mock_response(user_content)

    client = _get_client(config)
    attempts = config.max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            response = client.responses.create(
                model=config.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                timeout=config.timeout,
            )
            text = _extract_text_response(response)
            _emit_metrics(
                ok=bool(text),
                attempt=attempt,
                elapsed_ms=round((time.monotonic() - start) * 1000),
            )
            return text
        except Exception as exc:
            logger.warning(
                "AI provider attempt %s/%s failed: %s", attempt, attempts, exc
            )
            if attempt >= attempts:
                return ""
            time.sleep(config.retry_backoff * attempt)
    return ""


def generate_title(text: str, user: User) -> str:
    try:
        config = _load_config()
        prompt = "Generate a concise, engaging blog post title:\n" + text
        system = _build_system_prompt(user)
        result = _call_openai_response(config, system, prompt)
        return result or _fallback_title(text)
    except Exception:
        return _fallback_title(text)


def generate_excerpt(text: str, user: User) -> str:
    try:
        config = _load_config()
        prompt = "Generate a 1-2 sentence summary/excerpt for this post:\n" + text
        system = _build_system_prompt(user)
        result = _call_openai_response(config, system, prompt)
        return result or _fallback_excerpt(text)
    except Exception:
        return _fallback_excerpt(text)


def generate_seo_description(text: str, user: User) -> str:
    try:
        config = _load_config()
        prompt = "Write an SEO meta description (max 150 chars):\n" + text
        system = _build_system_prompt(user)
        result = _call_openai_response(config, system, prompt)
        return result or _fallback_seo(text)
    except Exception:
        return _fallback_seo(text)


def suggest_tags(text: str, user: User) -> List[str]:
    try:
        config = _load_config()
        prompt = "Suggest up to 5 comma-separated tags for this post:\n" + text
        system = _build_system_prompt(user)
        result = _call_openai_response(config, system, prompt)
        if result:
            tags = [t.strip().lower() for t in result.split(",") if t.strip()]
            return tags[:5]
    except Exception:
        pass
    return _fallback_tags(text)


def summarize_text(text: str, user: User) -> str:
    try:
        config = _load_config()
        prompt = "Summarize the following content in 3 bullet points:\n" + text
        system = _build_system_prompt(user)
        result = _call_openai_response(config, system, prompt)
        return result or _fallback_summary(text)
    except Exception:
        return _fallback_summary(text)


def moderate_text(text: str, user: User) -> Dict[str, str]:
    try:
        config = _load_config()
        prompt = (
            "Assess the following text for toxicity/harm. "
            "Return 'low' or 'high' risk and a numeric toxicity score 0-1."
        )
        system = _build_system_prompt(user)
        result = _call_openai_response(config, system, f"{prompt}\n{text}")
        if result:
            lower = result.lower()
            label = "high" if "high" in lower else "low"
            score = "0.8" if label == "high" else "0.05"
            return {"toxicity_score": float(score), "label": label}
    except Exception:
        pass
    return _fallback_moderation(text)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _extract_text_response(response) -> str:
    try:
        for output in response.output:
            for item in getattr(output, "content", []):
                if getattr(item, "type", "") == "output_text":
                    text = getattr(item, "text", "") or ""
                    return text.strip()
    except Exception:
        return ""
    return ""


def _mock_response(user_content: str) -> str:
    # Deterministic mock useful for tests and local dev without keys.
    snippet = (user_content or "").strip().split("\n")[0][:120]
    return f"[mock-ai] {snippet or 'No content provided.'}"


def _emit_metrics(*, ok: bool, attempt: int, elapsed_ms: int) -> None:
    try:
        logger.info(
            "ai.call",
            extra={
                "event": {
                    "ok": ok,
                    "attempt": attempt,
                    "elapsed_ms": elapsed_ms,
                }
            },
        )
    except Exception:
        # Metrics should never break the request flow
        return
