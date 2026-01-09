from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    pass


@dataclass
class AIProviderConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout: int = 30
    max_tokens: int = 1024
    temperature: float = 0.3
    allow_tools: bool = False
    log_prompts: bool = False
    log_completions: bool = False
    pii_redaction: bool = True
    moderation_enabled: bool = True
    retry_limit: int = 3
    backoff_min_seconds: float = 0.5
    backoff_max_seconds: float = 4.0


def _scrub(messages: list[dict[str, Any]], enabled: bool) -> list[dict[str, Any]]:
    if not enabled:
        return messages
    redacted = []
    for m in messages:
        content = m.get("content", "")
        for needle in ["@", ".com", ".net", ".org", "http://", "https://"]:
            content = content.replace(needle, "[redacted]")
        redacted.append({**m, "content": content})
    return redacted


def _backoff_iter(min_s: float, max_s: float, attempts: int):
    delay = min_s
    for _ in range(attempts):
        yield delay
        delay = min(delay * 2, max_s)


class DeepSeekClient:
    default_base = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, cfg: AIProviderConfig):
        self.cfg = cfg

    def send_chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self.cfg.model,
            "messages": messages,
            "max_tokens": self.cfg.max_tokens,
            "temperature": self.cfg.temperature,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cfg.api_key}",
        }
        url = self.cfg.base_url or self.default_base

        for delay in _backoff_iter(
            self.cfg.backoff_min_seconds,
            self.cfg.backoff_max_seconds,
            self.cfg.retry_limit,
        ):
            start = time.monotonic()
            try:
                resp = requests.post(
                    url,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=self.cfg.timeout,
                )
                latency_ms = int((time.monotonic() - start) * 1000)
                if resp.status_code == 429 or 500 <= resp.status_code < 600:
                    logger.warning(
                        "DeepSeek retryable error %s: %s", resp.status_code, resp.text
                    )
                    time.sleep(delay)
                    continue
                if resp.status_code != 200:
                    raise AIProviderError(
                        f"DeepSeek error {resp.status_code}: {resp.text}"
                    )
                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message", {}).get("content", "")
                usage = data.get("usage", {}) or {}
                return {
                    "text": message,
                    "latency_ms": latency_ms,
                    "usage": {
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                    },
                    "raw": data,
                }
            except (requests.Timeout, requests.ConnectionError) as exc:
                logger.warning("DeepSeek request timeout/connection error: %s", exc)
                time.sleep(delay)
                continue
        raise AIProviderError("DeepSeek request failed after retries")


def build_client(cfg: AIProviderConfig):
    provider = (cfg.provider or "").lower()
    if provider == "deepseek":
        return DeepSeekClient(cfg)
    raise AIProviderError(f"Unsupported AI provider: {cfg.provider}")


def send_chat(cfg: AIProviderConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    safe_messages = _scrub(messages, cfg.pii_redaction)
    client = build_client(cfg)
    result = client.send_chat(safe_messages)
    if cfg.log_prompts:
        logger.info(
            "AI prompt provider=%s model=%s messages=%s",
            cfg.provider,
            cfg.model,
            safe_messages,
        )
    if cfg.log_completions:
        logger.info(
            "AI completion provider=%s model=%s result=%s",
            cfg.provider,
            cfg.model,
            result,
        )
    return result
