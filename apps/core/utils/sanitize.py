
from __future__ import annotations

import re
from typing import Any, Iterable

from django.utils.text import slugify as django_slugify

try:
    import bleach  # type: ignore
except Exception:  # pragma: no cover
    bleach = None


def slugify(value: str, allow_unicode: bool = False, max_length: int | None = None) -> str:
    slug = django_slugify(value, allow_unicode=allow_unicode)
    if max_length:
        slug = slug[:max_length]
    return slug


def sanitize_html(html: str, allowed_tags: Iterable[str] | None = None, allowed_attrs: dict[str, Any] | None = None) -> str:
    if not html:
        return ""
    if bleach is None:
        # fallback: strip tags by regex
        return re.sub(r"<[^>]+>", "", html)
    tags = allowed_tags or ["p", "br", "strong", "em", "ul", "ol", "li", "a", "code"]
    attrs = allowed_attrs or {"a": ["href", "title", "rel", "target"]}
    cleaned = bleach.clean(html, tags=tags, attributes=attrs, strip=True, protocols=["http", "https", "mailto"])
    # Harden links: drop javascript/data schemes that might slip through, and enforce rel on target _blank
    def _sanitize_anchor(attrs, new=False):
        href = attrs.get("href", "")
        if href and not href.startswith(("http://", "https://", "mailto:")):
            attrs.pop("href", None)
        if attrs.get("target") == "_blank":
            attrs["rel"] = "nofollow noopener noreferrer"
        return attrs

    return bleach.clean(
        cleaned,
        tags=tags,
        attributes=attrs,
        strip=True,
        protocols=["http", "https", "mailto"],
        filters=[bleach.sanitizer.AttributeFilter(_sanitize_anchor)],
    )


