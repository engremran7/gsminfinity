
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.core import ai


@dataclass
class ModerationResult:
    label: str
    score: float
    rationale: str = ""


def classify_comment(text: str, context: Optional[str] = None) -> ModerationResult:
    """
    Lightweight AI moderation wrapper; in production add safety filters and caching.
    """
    prompt = (
        "Classify this comment for spam/toxicity/hate. Return a single label among "
        "['approved','pending','spam','abuse'] with a short rationale.\n"
        f"Comment: {text}\nContext: {context or ''}"
    )
    raw = ai.safe_generate_text(prompt, context="comment_moderation")
    label = "pending"
    score = 0.5
    if raw:
        lower = raw.lower()
        if "spam" in lower:
            label = "spam"
        elif "abuse" in lower or "toxic" in lower or "hate" in lower:
            label = "abuse"
        elif "approve" in lower or "clean" in lower:
            label = "approved"
    return ModerationResult(label=label, score=score, rationale=raw or "")


