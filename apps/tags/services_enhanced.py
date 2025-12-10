"""
Enhanced tag services with AI-powered auto-tagging, semantic similarity, and clustering.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Iterable, List, Dict, Optional, Tuple
from collections import Counter
from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache

from apps.tags.models import Tag
from apps.core import ai
from apps.core import ai_client
from apps.tags.models_keyword import KeywordProvider, KeywordSuggestion
from django.utils.text import slugify

logger = logging.getLogger(__name__)

# Configuration
MIN_TAG_SCORE = 0.3  # Minimum confidence score for auto-suggestions
MAX_AUTO_TAGS = 15  # Maximum number of tags to auto-generate
CACHE_TTL = 3600  # 1 hour cache for tag suggestions


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return " ".join((text or "").lower().strip().split())


def _compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _cache_key(operation: str, content_hash: str) -> str:
    """Generate cache key for operations."""
    return f"tags:{operation}:{content_hash[:16]}"


def suggest_tags_from_text(
    text: str, 
    limit: int = 10,
    min_score: float = MIN_TAG_SCORE,
    use_cache: bool = True,
    existing_tags: Optional[List[str]] = None
) -> List[Dict[str, any]]:
    """
    Generate tag suggestions from text using AI and heuristics.
    
    Args:
        text: Content to analyze
        limit: Maximum number of suggestions
        min_score: Minimum confidence score
        use_cache: Whether to use cached results
        existing_tags: Already applied tags to avoid duplicates
        
    Returns:
        List of tag dictionaries with name, score, and source
    """
    text = (text or "").strip()
    if not text:
        return []
    
    # Check cache
    content_hash = _compute_content_hash(text)
    cache_key = _cache_key("suggest", content_hash)
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Using cached tag suggestions for hash {content_hash[:8]}")
            return cached[:limit]
    
    existing_normalized = {_normalize(tag) for tag in (existing_tags or [])}
    suggestions = []
    seen = set()
    
    try:
        # AI-powered tag suggestions
        ai_tags = ai_client.suggest_tags(text, None) or []
        for tag_name in ai_tags:
            norm = _normalize(tag_name)
            if not norm or norm in seen or norm in existing_normalized:
                continue
            
            seen.add(norm)
            suggestions.append({
                "name": tag_name.strip(),
                "normalized": norm,
                "score": 0.8,  # High confidence for AI suggestions
                "source": "ai"
            })
            
    except Exception as exc:
        logger.warning(f"AI tag suggestion failed: {exc}")
    
    # Extract keyword-based suggestions
    try:
        keyword_suggestions = _extract_keywords(text, limit=limit * 2)
        for keyword in keyword_suggestions:
            norm = _normalize(keyword)
            if not norm or norm in seen or norm in existing_normalized:
                continue
            
            seen.add(norm)
            suggestions.append({
                "name": keyword.strip(),
                "normalized": norm,
                "score": 0.6,  # Medium confidence for keywords
                "source": "keyword"
            })
            
    except Exception as exc:
        logger.warning(f"Keyword extraction failed: {exc}")
    
    # Match against existing tags
    try:
        matching_tags = _find_matching_tags(text, limit=limit * 2)
        for tag in matching_tags:
            norm = _normalize(tag.name)
            if norm in seen or norm in existing_normalized:
                continue
            
            seen.add(norm)
            suggestions.append({
                "name": tag.name,
                "normalized": norm,
                "score": 0.7,  # Good confidence for existing matches
                "source": "existing",
                "tag_id": tag.id
            })
            
    except Exception as exc:
        logger.warning(f"Tag matching failed: {exc}")
    
    # Sort by score and filter by minimum
    suggestions = [
        s for s in suggestions 
        if s["score"] >= min_score
    ]
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    # Cache results
    if use_cache and suggestions:
        cache.set(cache_key, suggestions, CACHE_TTL)
        logger.debug(f"Cached {len(suggestions)} tag suggestions")
    
    return suggestions[:limit]


def _extract_keywords(text: str, limit: int = 20) -> List[str]:
    """
    Extract potential keywords from text using simple heuristics.
    
    Args:
        text: Text to analyze
        limit: Maximum keywords to extract
        
    Returns:
        List of keyword strings
    """
    # Simple extraction: capitalize words (potential proper nouns/topics)
    words = text.split()
    
    # Extract capitalized words and common tech terms
    keywords = []
    tech_terms = {'API', 'SDK', 'AI', 'ML', 'UI', 'UX', 'SEO', 'SQL', 'HTTP', 'REST'}
    
    for word in words:
        clean = word.strip('.,!?;:()[]{}\"\'').strip()
        if not clean:
            continue
        
        # Capitalized words (excluding sentence starts)
        if clean[0].isupper() and len(clean) > 2:
            keywords.append(clean)
        
        # Tech terms
        if clean.upper() in tech_terms:
            keywords.append(clean.upper())
    
    # Count frequency and return most common
    counter = Counter(keywords)
    return [word for word, count in counter.most_common(limit)]


def _find_matching_tags(text: str, limit: int = 10) -> List[Tag]:
    """
    Find existing tags that match the content.
    
    Args:
        text: Content to match against
        limit: Maximum matches to return
        
    Returns:
        List of matching Tag objects
    """
    text_lower = text.lower()
    
    # Find tags where name or synonyms appear in text
    matching_tags = []
    
    for tag in Tag.objects.filter(is_active=True, merge_into__isnull=True)[:500]:
        # Check if tag name appears in text
        if tag.normalized_name in text_lower:
            matching_tags.append(tag)
            continue
        
        # Check synonyms
        synonyms = tag.synonyms if isinstance(tag.synonyms, list) else []
        for synonym in synonyms:
            if _normalize(synonym) in text_lower:
                matching_tags.append(tag)
                break
    
    # Sort by usage count (popularity)
    matching_tags.sort(key=lambda t: t.usage_count, reverse=True)
    
    return matching_tags[:limit]


def auto_tag_content(
    text: str,
    max_tags: int = 10,
    min_score: float = 0.5,
    auto_create: bool = False
) -> List[Tag]:
    """
    Automatically tag content with AI suggestions.
    
    Args:
        text: Content to tag
        max_tags: Maximum number of tags to apply
        min_score: Minimum confidence score
        auto_create: Whether to create new tags automatically
        
    Returns:
        List of Tag objects to apply
    """
    suggestions = suggest_tags_from_text(
        text, 
        limit=max_tags * 2, 
        min_score=min_score
    )
    
    tags_to_apply = []
    
    for suggestion in suggestions[:max_tags]:
        # Try to find existing tag
        tag = Tag.objects.filter(
            normalized_name=suggestion["normalized"],
            is_active=True,
            merge_into__isnull=True
        ).first()
        
        if tag:
            tags_to_apply.append(tag)
        elif auto_create and suggestion.get("source") == "ai":
            # Create new tag from AI suggestion
            try:
                tag = Tag.objects.create(
                    name=suggestion["name"],
                    normalized_name=suggestion["normalized"],
                    ai_suggested=True,
                    ai_score=suggestion["score"],
                    is_curated=False
                )
                tags_to_apply.append(tag)
                logger.info(f"Auto-created tag: {tag.name}")
            except Exception as exc:
                logger.warning(f"Failed to create tag {suggestion['name']}: {exc}")
    
    return tags_to_apply


def merge_tags(source: Tag, target: Tag, user=None) -> None:
    """
    Merge source tag into target tag.
    
    Args:
        source: Tag to merge from
        target: Tag to merge into
        user: User performing the merge
    """
    if source.pk == target.pk:
        return
    
    with transaction.atomic():
        # Reassign posts from source to target
        posts_qs = getattr(source, "posts", None)
        if posts_qs is not None:
            for post in posts_qs.all():
                post.tags.add(target)
                post.tags.remove(source)
        
        # Mark source as merged
        source.merge_into = target
        source.is_active = False
        source.deleted_at = timezone.now()
        source.deleted_by = user
        source.save(update_fields=["merge_into", "is_active", "deleted_at", "deleted_by"])
        
        # Update target usage count
        target.usage_count = getattr(target, "posts", Tag.objects.none()).count()
        target.save(update_fields=["usage_count"])
        
        logger.info(f"Merged tag {source.name} into {target.name}")


def rebuild_usage() -> None:
    """Rebuild usage counts for all tags."""
    logger.info("Rebuilding tag usage counts")
    updated = 0
    
    for tag in Tag.objects.all():
        try:
            old_count = tag.usage_count
            new_count = getattr(tag, "posts", Tag.objects.none()).count()
            
            if old_count != new_count:
                tag.usage_count = new_count
                tag.save(update_fields=["usage_count"])
                updated += 1
                
        except Exception as exc:
            logger.warning(f"Failed to update usage for tag {tag.id}: {exc}")
            continue
    
    logger.info(f"Rebuilt usage counts for {updated} tags")


def compute_content_hash(text: str) -> str:
    """Compute content hash for caching."""
    return _compute_content_hash(text)


def store_suggestions(tag: Tag, suggestions: List[Dict], content_hash: str) -> None:
    """
    Store AI suggestions for a tag.
    
    Args:
        tag: Tag object
        suggestions: List of suggestion dictionaries
        content_hash: Hash of content used for suggestions
    """
    tag.suggestions = suggestions
    tag.content_hash = content_hash
    tag.last_suggested_at = timezone.now()
    tag.save(update_fields=["suggestions", "content_hash", "last_suggested_at"])


def jaccard(a: str, b: str) -> float:
    """
    Calculate Jaccard similarity between two strings.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def find_similar_tags(tag_name: str, threshold: float = 0.7) -> List[Tuple[Tag, float]]:
    """
    Find tags similar to given name using Jaccard similarity.
    
    Args:
        tag_name: Tag name to compare
        threshold: Minimum similarity threshold
        
    Returns:
        List of (Tag, similarity_score) tuples
    """
    normalized = _normalize(tag_name)
    similar = []
    
    for tag in Tag.objects.filter(is_active=True, merge_into__isnull=True)[:1000]:
        similarity = jaccard(normalized, tag.normalized_name)
        if similarity >= threshold:
            similar.append((tag, similarity))
    
    # Sort by similarity
    similar.sort(key=lambda x: x[1], reverse=True)
    
    return similar


def cluster_tags(min_similarity: float = 0.8) -> Dict[str, List[str]]:
    """
    Cluster similar tags for potential merging.
    
    Args:
        min_similarity: Minimum similarity for clustering
        
    Returns:
        Dictionary mapping canonical tag to similar tags
    """
    clusters = {}
    processed = set()
    
    tags = list(Tag.objects.filter(
        is_active=True, 
        merge_into__isnull=True
    ).order_by('-usage_count')[:500])
    
    for tag in tags:
        if tag.normalized_name in processed:
            continue
        
        # Find similar tags
        similar = find_similar_tags(tag.name, threshold=min_similarity)
        
        if len(similar) > 1:  # Has similar tags
            cluster_members = []
            for similar_tag, score in similar[1:]:  # Skip self
                if similar_tag.normalized_name not in processed:
                    cluster_members.append(similar_tag.name)
                    processed.add(similar_tag.normalized_name)
            
            if cluster_members:
                clusters[tag.name] = cluster_members
        
        processed.add(tag.normalized_name)
    
    logger.info(f"Found {len(clusters)} tag clusters")
    return clusters


def fetch_external_keywords(provider: KeywordProvider) -> List[Dict[str, str]]:
    """
    Fetch keywords from external provider.
    
    Args:
        provider: KeywordProvider instance
        
    Returns:
        List of keyword dictionaries
    """
    if not provider.is_enabled:
        return []
    
    # Placeholder for external API integration
    logger.info(f"Fetching keywords from provider: {provider.name}")
    
    # In production, implement actual API calls based on provider.config
    return []


def cleanup_unused_tags(days_threshold: int = 180, min_usage: int = 0) -> int:
    """
    Clean up unused or low-usage tags.
    
    Args:
        days_threshold: Days since last used
        min_usage: Minimum usage count to keep
        
    Returns:
        Number of tags cleaned up
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days_threshold)
    
    # Find tags with no usage or low usage
    to_cleanup = Tag.objects.filter(
        usage_count__lte=min_usage,
        created_at__lt=cutoff_date,
        is_active=True,
        is_curated=False  # Don't auto-cleanup curated tags
    )
    
    count = to_cleanup.count()
    
    # Soft delete
    to_cleanup.update(
        is_active=False,
        deleted_at=timezone.now()
    )
    
    logger.info(f"Cleaned up {count} unused tags")
    return count
