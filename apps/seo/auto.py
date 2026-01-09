from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.seo.models import Metadata, SchemaEntry, SEOModel
from apps.seo.models_settings import SeoAutomationSettings
from apps.tags.models import Tag

# Lightweight stopwords to avoid extra dependencies; extendable via settings
DEFAULT_STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "have",
    "has",
    "are",
    "was",
    "were",
    "will",
    "shall",
    "should",
    "would",
    "could",
    "about",
    "into",
    "onto",
    "over",
    "under",
    "also",
    "very",
    "really",
    "your",
    "you",
    "our",
    "ours",
    "their",
    "theirs",
    "his",
    "her",
    "its",
}


def _get_setting(name: str, default):
    try:
        ss = SeoAutomationSettings.get_solo()
        return getattr(ss, name)
    except Exception:
        return getattr(settings, name, default)


def suggest_tags(
    texts: Iterable[str], max_tags: int = 8, min_len: int = 4
) -> list[tuple[str, float]]:
    """
    Very lightweight keyword extractor: counts frequent words > min_len, excludes stopwords.
    Returns list of (tag, score).
    """
    stop = set(DEFAULT_STOPWORDS) | set(_get_setting("SEO_STOPWORDS", []))
    counts: Counter[str] = Counter()
    for text in texts:
        if not text:
            continue
        for word in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower()):
            if len(word) < min_len or word in stop:
                continue
            counts[word] += 1
    top = counts.most_common(max_tags)
    return [(w.replace("-", " ").title(), float(c)) for w, c in top]


def ensure_canonical(post) -> str:
    if getattr(post, "canonical_url", ""):
        return post.canonical_url
    try:
        url = reverse("blog:post_detail", kwargs={"slug": post.slug})
    except Exception:
        url = ""
    return url


def ensure_metadata(post) -> Metadata:
    ct = ContentType.objects.get_for_model(post.__class__)
    seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=post.pk)
    meta, _ = Metadata.objects.get_or_create(seo=seo_obj)
    if not meta.meta_title:
        meta.meta_title = post.seo_title or post.title
    if not meta.meta_description:
        meta.meta_description = (post.seo_description or post.summary or "")[:320]
    if not meta.canonical_url:
        meta.canonical_url = ensure_canonical(post)
    meta.generated_at = meta.generated_at or timezone.now()
    meta.save()
    return meta


def ensure_article_schema(post) -> None:
    if not _get_setting("SEO_AUTO_SCHEMA", True):
        return
    try:
        ct = ContentType.objects.get_for_model(post.__class__)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=post.pk)
        SchemaEntry.objects.update_or_create(
            seo=seo_obj,
            schema_type="Article",
            defaults={
                "payload": {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": post.title,
                    "description": post.seo_description or post.summary or "",
                    "datePublished": (
                        post.publish_at or post.published_at or timezone.now()
                    ).isoformat(),
                    "dateModified": (post.updated_at or timezone.now()).isoformat(),
                    "author": {
                        "@type": "Person",
                        "name": getattr(
                            getattr(post, "author", None), "get_full_name", lambda: ""
                        )()
                        or getattr(getattr(post, "author", None), "username", ""),
                    },
                    "mainEntityOfPage": {
                        "@type": "WebPage",
                        "@id": ensure_canonical(post),
                    },
                },
            },
        )
    except Exception:
        return


def ensure_breadcrumb_schema(post) -> None:
    if not _get_setting("SEO_AUTO_SCHEMA", True):
        return
    try:
        ct = ContentType.objects.get_for_model(post.__class__)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=post.pk)
        SchemaEntry.objects.update_or_create(
            seo=seo_obj,
            schema_type="BreadcrumbList",
            defaults={
                "payload": {
                    "@context": "https://schema.org",
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": 1,
                            "name": "Home",
                            "item": "/",
                        },
                        {
                            "@type": "ListItem",
                            "position": 2,
                            "name": "Blog",
                            "item": "/blog/",
                        },
                        {
                            "@type": "ListItem",
                            "position": 3,
                            "name": post.title,
                            "item": ensure_canonical(post),
                        },
                    ],
                },
            },
        )
    except Exception:
        return


def apply_auto_tags(post, max_tags: int = 6) -> list[Tag]:
    if not _get_setting("auto_tags", True):
        return []

    suggestions = []
    # Try AI first
    try:
        from apps.ai.services import get_settings, test_completion

        ai_settings = get_settings()
        if ai_settings.get("ai_enabled"):
            prompt = f"Generate {max_tags} relevant tags for the following blog post. Return ONLY a comma-separated list of tags.\n\nTitle: {post.title}\nSummary: {post.summary}\n\nTags:"
            response = test_completion(prompt)
            text = response.get("text", "")
            if text:
                tags = [t.strip() for t in text.split(",") if t.strip()]
                suggestions = [(t, 1.0) for t in tags[:max_tags]]
    except Exception:
        pass

    if not suggestions:
        suggestions = suggest_tags(
            [post.title, post.summary or "", post.body], max_tags=max_tags
        )

    attached: list[Tag] = []
    suggest_only = _get_setting("suggest_only", False)
    for name, score in suggestions:
        try:
            slug = slugify(name)[:80]
            tag, _ = Tag.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name[:64],
                    "normalized_name": name.lower()[:64],
                    "ai_suggested": True,
                    "ai_score": score,
                },
            )
            attached.append(tag)
        except Exception:
            continue
    if attached and not suggest_only:
        post.tags.add(*attached)
    return attached


def apply_post_seo(post) -> None:
    """
    Main entry point: ensure metadata, schemas, canonical, and auto-tags.
    """
    if not _get_setting("auto_meta", True):
        return

    meta = ensure_metadata(post)
    if _get_setting("auto_schema", True):
        ensure_article_schema(post)
        ensure_breadcrumb_schema(post)

    if _get_setting("auto_tags", True):
        apply_auto_tags(post)

    # Return meta for callers if needed
    return meta
