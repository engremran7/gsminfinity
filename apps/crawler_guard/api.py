
"""
Public API for the crawler_guard micro-module.
Intentionally lightweight to be loaded via AppService.get("crawler_guard").
"""
from __future__ import annotations

from typing import Iterable, Optional

from apps.crawler_guard.models import CrawlerEvent, CrawlerRule


def active_rules() -> Iterable[CrawlerRule]:
    return CrawlerRule.objects.filter(is_enabled=True)


def log_event(**kwargs) -> Optional[CrawlerEvent]:
    try:
        return CrawlerEvent.objects.create(**kwargs)
    except Exception:
        return None


__all__ = ["active_rules", "log_event"]


