from __future__ import annotations

from apps.core import ai_client
from apps.core.utils import feature_flags


def generate_metadata(text: str, user) -> dict:
    if not feature_flags.seo_enabled() or not feature_flags.auto_meta_enabled():
        return {}
    title = ai_client.generate_title(text, user)
    description = ai_client.generate_excerpt(text, user)
    keywords = ", ".join(ai_client.suggest_tags(text, user))
    return {
        "meta_title": title,
        "meta_description": description,
        "focus_keywords": [k.strip() for k in keywords.split(",") if k.strip()],
    }
