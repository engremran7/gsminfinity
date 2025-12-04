
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


def sanitize_html(
    html: str,
    allowed_tags: Iterable[str] | None = None,
    allowed_attrs: dict[str, Any] | None = None,
    allowed_iframe_prefixes: Iterable[str] | None = None,
) -> str:
    if not html:
        return ""
    if bleach is None:
        # fallback: strip tags by regex
        return re.sub(r"<[^>]+>", "", html)
    tags = allowed_tags or [
        "p",
        "br",
        "strong",
        "em",
        "ul",
        "ol",
        "li",
        "a",
        "code",
        "blockquote",
        "h3",
        "h4",
        "h5",
        "iframe",
    ]
    attrs = allowed_attrs or {
        "a": ["href", "title", "rel", "target"],
        "iframe": ["src", "width", "height", "frameborder", "allow", "allowfullscreen", "class", "title"],
    }
    cleaned = bleach.clean(html, tags=tags, attributes=attrs, strip=True, protocols=["http", "https", "mailto"])
    # Harden links: drop javascript/data schemes that might slip through, and enforce rel on target _blank
    def _sanitize_anchor(attrs, new=False):
        href = attrs.get("href", "")
        if href and not href.startswith(("http://", "https://", "mailto:")):
            attrs.pop("href", None)
        if attrs.get("target") == "_blank":
            attrs["rel"] = "nofollow noopener noreferrer"
        return attrs

    result = bleach.clean(
        cleaned,
        tags=tags,
        attributes=attrs,
        strip=True,
        protocols=["http", "https", "mailto"],
        filters=[bleach.sanitizer.AttributeFilter(_sanitize_anchor)],
    )
    # Drop iframes not on the allowed prefix list
    if "iframe" in tags:
        prefixes = tuple(allowed_iframe_prefixes or ("https://www.youtube.com/embed/", "https://player.vimeo.com/"))
        def _strip_invalid_iframes(match):
            src = match.group(1) or ""
            return match.group(0) if src.startswith(prefixes) else ""
        result = re.sub(r'<iframe[^>]+src="([^"]+)"[^>]*></iframe>', _strip_invalid_iframes, result, flags=re.IGNORECASE)
    return result


