from __future__ import annotations

from apps.core import ai_client
from apps.core.utils import feature_flags


def generate_schema(text: str, user) -> dict:
    """
    Placeholder: leverage AI to produce JSON-LD schema hints.
    """
    if not feature_flags.seo_enabled() or not feature_flags.auto_schema_enabled():
        return {}
    schema_text = ai_client.generate_excerpt(text, user)
    return {"@context": "https://schema.org", "@type": "Article", "description": schema_text}
