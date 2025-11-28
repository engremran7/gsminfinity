from __future__ import annotations

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


def readability_score(text: str) -> Dict[str, float]:
    """
    Lightweight readability heuristic (Flesch-like).
    """
    try:
        sentences = max(1, text.count(".") + text.count("!") + text.count("?"))
        words = max(1, len(re.findall(r"\\w+", text)))
        syllables = max(1, len(re.findall(r"[aeiouy]+", text, re.I)))
        flesch = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
        score = round(max(0, min(100, flesch)), 1)
        logger.info("seo.readability", extra={"event": {"score": score}})
        return {"readability": score}
    except Exception as exc:
        logger.warning("readability_score failed: %s", exc)
        return {"readability": 0.0}
