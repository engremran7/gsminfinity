from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger(__name__)


def serp_analyze(meta_title: str, meta_description: str) -> Dict[str, float]:
    """
    Placeholder SERP analyzer that returns a simple heuristic score.
    """
    try:
        length_score = min(len(meta_title) / 60.0, 1.0)
        desc_score = min(len(meta_description) / 160.0, 1.0)
        score = round((length_score * 0.6 + desc_score * 0.4) * 100, 1)
        logger.info("seo.serp.analyze", extra={"event": {"score": score}})
        return {"serp_score": score}
    except Exception as exc:
        logger.warning("serp_analyze failed: %s", exc)
        return {"serp_score": 0.0}
