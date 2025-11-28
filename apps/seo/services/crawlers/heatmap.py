from __future__ import annotations

import logging
from typing import Dict, Iterable

from apps.seo.models import SitemapEntry

logger = logging.getLogger(__name__)


def heatmap() -> Dict[str, int]:
    """
    Produce a basic heatmap of sitemap statuses.
    """
    try:
        total = SitemapEntry.objects.count()
        errors = SitemapEntry.objects.filter(last_status__gte=400).count()
        unknown = SitemapEntry.objects.filter(last_status__isnull=True).count()
        ok = total - errors - unknown
        logger.info("seo.heatmap", extra={"event": {"total": total, "errors": errors, "unknown": unknown}})
        return {"total": total, "ok": ok, "errors": errors, "unknown": unknown}
    except Exception as exc:
        logger.warning("heatmap generation failed: %s", exc)
        return {"total": 0, "ok": 0, "errors": 0, "unknown": 0}
