
from __future__ import annotations

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def analyze_performance(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Lightweight heuristic optimizer. In production, offload to Celery and persist to DB.
    Returns suggestions such as pause/boost creatives or adjust aggressiveness.
    """
    suggestions = []
    for row in metrics:
        ctr = row.get("ctr", 0)
        impressions = row.get("impressions", 0)
        creative_id = row.get("creative_id")
        if creative_id is None:
            continue
        if impressions >= 100 and ctr < 0.2:
            suggestions.append(
                {
                    "creative_id": creative_id,
                    "action": "pause",
                    "reason": f"Low CTR ({ctr:.2f}) after {impressions} impressions",
                }
            )
        elif ctr >= 1.5:
            suggestions.append(
                {
                    "creative_id": creative_id,
                    "action": "boost",
                    "reason": f"High CTR ({ctr:.2f}); consider higher weight",
                }
            )
    logger.debug("AI optimizer suggestions=%s", suggestions)
    return suggestions


