from __future__ import annotations

from typing import List, Iterable, Optional
from collections import Counter

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from apps.seo.models import LinkableEntity, LinkSuggestion
from apps.core.utils import feature_flags
from apps.core import ai


def refresh_linkable_entity(obj, title: str, url: str, keywords: str = ""):
    if not feature_flags.seo_enabled():
        return None
    ct = ContentType.objects.get_for_model(obj.__class__)
    defaults = {
        "title": title,
        "url": url,
        "keywords": keywords.split(",") if isinstance(keywords, str) else (keywords or []),
        "is_active": True,
    }
    # Optional embedding if enabled
    try:
        if feature_flags.auto_linking_enabled():
            vec = ai.embed_text(f"{title}\n{keywords}")
            defaults["embedding"] = vec
            defaults["vector"] = vec
    except Exception:
        pass
    entity, _ = LinkableEntity.objects.update_or_create(
        content_type=ct,
        object_id=obj.pk,
        defaults=defaults,
    )
    return entity


def _eligible_candidates(source: LinkableEntity, candidates: Iterable[LinkableEntity]) -> List[LinkableEntity]:
    seen = {source.pk}
    out: List[LinkableEntity] = []
    for c in candidates:
        if not c or c.pk in seen:
            continue
        seen.add(c.pk)
        out.append(c)
    return out


def _score_candidate(source: LinkableEntity, target: LinkableEntity) -> float:
    """
    Lightweight semantic-ish score:
    - keyword overlap (bag-of-words)
    - title overlap
    """
    src_terms = Counter((source.keywords or "").lower().split())
    tgt_terms = Counter((target.keywords or "").lower().split())
    overlap = sum((src_terms & tgt_terms).values())

    title_overlap = 0
    if source.title and target.title:
        src_title = set(source.title.lower().split())
        tgt_title = set(target.title.lower().split())
        title_overlap = len(src_title & tgt_title)

    return float(overlap + title_overlap * 0.5)


def suggest_links(source: LinkableEntity, candidates: List[LinkableEntity], limit: int = 5):
    """
    Keyword-first suggestions with stability: we do not churn locked suggestions,
    cap updates to the provided limit, and order by simple similarity scoring.
    """
    if not feature_flags.seo_enabled() or not feature_flags.auto_linking_enabled():
        return

    allowed = _eligible_candidates(source, candidates)
    LinkSuggestion.objects.filter(source=source, locked=False).delete()

    ranked = sorted(allowed, key=lambda t: _score_candidate(source, t), reverse=True)
    added = 0
    for target in ranked:
        if added >= limit:
            break
        score = _score_candidate(source, target)
        LinkSuggestion.objects.update_or_create(
            source=source,
            target=target,
            defaults={"score": score, "is_applied": False, "locked": False},
        )
        added += 1
