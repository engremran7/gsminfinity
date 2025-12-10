"""
Enhanced SEO services with AI-powered optimization, automated metadata generation, and schema markup.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.seo.models import SEOModel, Metadata, SchemaEntry
from apps.core import ai
from apps.core import ai_client

logger = logging.getLogger(__name__)

# Configuration
META_TITLE_MAX = 60  # Google displays ~60 chars
META_DESC_MAX = 155  # Google displays ~155 chars
SOCIAL_TITLE_MAX = 70  # Social platforms
SOCIAL_DESC_MAX = 200
CACHE_TTL = 1800  # 30 minutes


def _compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _truncate_smart(text: str, max_length: int) -> str:
    """
    Truncate text at word boundary within max_length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    # Find last space before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # Only use if space is reasonably close
        return truncated[:last_space] + "..."
    
    return truncated + "..."


def generate_meta_title(
    content: str,
    title: str = None,
    keywords: List[str] = None,
    use_cache: bool = True
) -> str:
    """
    Generate SEO-optimized meta title using AI.
    
    Args:
        content: Page content
        title: Existing title (optional)
        keywords: Target keywords (optional)
        use_cache: Whether to use cached results
        
    Returns:
        Optimized meta title
    """
    if not content or not content.strip():
        return title[:META_TITLE_MAX] if title else ""
    
    # Check cache
    cache_key = f"seo:meta_title:{_compute_content_hash(content + (title or ''))[:16]}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Using cached meta title")
            return cached
    
    try:
        # Build prompt with context
        keyword_context = f" Focus on these keywords: {', '.join(keywords)}" if keywords else ""
        prompt = (
            f"Generate an SEO-optimized meta title (max {META_TITLE_MAX} characters) "
            f"for this content.{keyword_context} Make it compelling and clickable. "
            "Include primary keyword near the beginning. Return only the title.\\n\\n"
            f"Content: {content[:2000]}\\n"
            f"Current title: {title or 'None'}"
        )
        
        result = ai.safe_generate_text(prompt, context="seo_title") or title or ""
        
        # Clean and validate
        result = result.strip().strip('"\\'')
        result = _truncate_smart(result, META_TITLE_MAX)
        
        # Cache result
        if result and use_cache:
            cache.set(cache_key, result, CACHE_TTL)
        
        return result
        
    except Exception as exc:
        logger.error(f"Meta title generation failed: {exc}", exc_info=True)
        # Fallback to title or first sentence
        return _truncate_smart(title or content.split('.')[0], META_TITLE_MAX)


def generate_meta_description(
    content: str,
    title: str = None,
    keywords: List[str] = None,
    use_cache: bool = True
) -> str:
    """
    Generate SEO-optimized meta description using AI.
    
    Args:
        content: Page content
        title: Page title (optional)
        keywords: Target keywords (optional)
        use_cache: Whether to use cached results
        
    Returns:
        Optimized meta description
    """
    if not content or not content.strip():
        return ""
    
    # Check cache
    cache_key = f"seo:meta_desc:{_compute_content_hash(content + (title or ''))[:16]}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Using cached meta description")
            return cached
    
    try:
        keyword_context = f" Include these keywords naturally: {', '.join(keywords)}" if keywords else ""
        prompt = (
            f"Generate an SEO-optimized meta description (max {META_DESC_MAX} characters) "
            f"for this content.{keyword_context} Make it compelling and include a call-to-action. "
            "Return only the description.\\n\\n"
            f"Title: {title or 'None'}\\n"
            f"Content: {content[:2000]}"
        )
        
        result = ai.safe_generate_text(prompt, context="seo_description") or ""
        
        # Clean and validate
        result = result.strip().strip('"\\'')
        result = _truncate_smart(result, META_DESC_MAX)
        
        # Cache result
        if result and use_cache:
            cache.set(cache_key, result, CACHE_TTL)
        
        return result
        
    except Exception as exc:
        logger.error(f"Meta description generation failed: {exc}", exc_info=True)
        # Fallback to first sentences
        sentences = content.split('.')[:2]
        return _truncate_smart('. '.join(sentences), META_DESC_MAX)


def extract_keywords(
    content: str,
    max_keywords: int = 10,
    use_cache: bool = True
) -> List[str]:
    """
    Extract relevant keywords from content using AI.
    
    Args:
        content: Content to analyze
        max_keywords: Maximum keywords to extract
        use_cache: Whether to use cached results
        
    Returns:
        List of extracted keywords
    """
    if not content or not content.strip():
        return []
    
    # Check cache
    cache_key = f"seo:keywords:{_compute_content_hash(content)[:16]}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Using cached keywords")
            return cached
    
    try:
        prompt = (
            f"Extract the {max_keywords} most important SEO keywords/phrases from this content. "
            "Return only a comma-separated list of keywords. Focus on topics, not common words.\\n\\n"
            f"Content: {content[:3000]}"
        )
        
        result = ai.safe_generate_text(prompt, context="seo_keywords") or ""
        
        # Parse comma-separated keywords
        keywords = [
            kw.strip().lower() 
            for kw in result.split(',') 
            if kw.strip() and len(kw.strip()) > 2
        ][:max_keywords]
        
        # Cache result
        if keywords and use_cache:
            cache.set(cache_key, keywords, CACHE_TTL)
        
        return keywords
        
    except Exception as exc:
        logger.error(f"Keyword extraction failed: {exc}", exc_info=True)
        return []


def generate_schema_markup(
    content_type: str,
    data: Dict[str, Any],
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Generate JSON-LD schema markup for content.
    
    Args:
        content_type: Type of content (Article, BlogPosting, Product, etc.)
        data: Content data (title, description, author, etc.)
        use_cache: Whether to use cached results
        
    Returns:
        Schema.org JSON-LD markup
    """
    # Check cache
    cache_key = f"seo:schema:{content_type}:{_compute_content_hash(json.dumps(data, sort_keys=True))[:16]}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Using cached schema markup")
            return cached
    
    schema = {
        "@context": "https://schema.org",
        "@type": content_type
    }
    
    # Map common fields
    field_mapping = {
        "title": "headline",
        "description": "description",
        "author": "author",
        "published_at": "datePublished",
        "updated_at": "dateModified",
        "image": "image",
        "url": "url",
    }
    
    for key, schema_key in field_mapping.items():
        if key in data and data[key]:
            value = data[key]
            
            # Handle datetime objects
            if isinstance(value, datetime):
                value = value.isoformat()
            
            # Handle author object
            if key == "author" and isinstance(value, dict):
                schema[schema_key] = {
                    "@type": "Person",
                    "name": value.get("name", ""),
                    "url": value.get("url", "")
                }
            else:
                schema[schema_key] = value
    
    # Add publisher info if available
    if "publisher" in data:
        schema["publisher"] = {
            "@type": "Organization",
            "name": data["publisher"].get("name", ""),
            "logo": {
                "@type": "ImageObject",
                "url": data["publisher"].get("logo", "")
            }
        }
    
    # Cache result
    if use_cache:
        cache.set(cache_key, schema, CACHE_TTL)
    
    return schema


def optimize_content_for_seo(
    content: str,
    target_keywords: List[str],
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Analyze and suggest SEO optimizations for content.
    
    Args:
        content: Content to analyze
        target_keywords: Target keywords for optimization
        use_cache: Whether to use cached results
        
    Returns:
        Dictionary with analysis and suggestions
    """
    if not content or not content.strip():
        return {"score": 0, "suggestions": [], "issues": ["Content is empty"]}
    
    # Check cache
    cache_key = f"seo:optimize:{_compute_content_hash(content + ''.join(target_keywords))[:16]}"
    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Using cached SEO analysis")
            return cached
    
    analysis = {
        "score": 0,
        "suggestions": [],
        "issues": [],
        "keyword_density": {},
        "readability": {}
    }
    
    content_lower = content.lower()
    word_count = len(content.split())
    
    # Basic SEO checks
    if word_count < 300:
        analysis["issues"].append("Content is too short (minimum 300 words recommended)")
        analysis["score"] -= 20
    elif word_count > 2000:
        analysis["suggestions"].append("Consider breaking up long content into multiple pages")
    
    # Keyword analysis
    for keyword in target_keywords:
        keyword_lower = keyword.lower()
        count = content_lower.count(keyword_lower)
        density = (count / word_count) * 100 if word_count > 0 else 0
        
        analysis["keyword_density"][keyword] = {
            "count": count,
            "density": round(density, 2)
        }
        
        if count == 0:
            analysis["issues"].append(f"Target keyword '{keyword}' not found in content")
            analysis["score"] -= 10
        elif density < 0.5:
            analysis["suggestions"].append(f"Increase usage of keyword '{keyword}' (current: {density:.1f}%)")
        elif density > 3.0:
            analysis["issues"].append(f"Keyword '{keyword}' used too frequently (keyword stuffing)")
            analysis["score"] -= 15
        else:
            analysis["score"] += 10
    
    # Readability checks
    sentences = content.split('.')
    avg_sentence_length = word_count / len(sentences) if sentences else 0
    
    analysis["readability"] = {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "avg_sentence_length": round(avg_sentence_length, 1)
    }
    
    if avg_sentence_length > 25:
        analysis["suggestions"].append("Consider using shorter sentences for better readability")
    
    # Heading structure check
    if '<h1' not in content and '<h2' not in content:
        analysis["issues"].append("Add headings (H1, H2) to structure content")
        analysis["score"] -= 15
    
    # Cap score at 100
    analysis["score"] = max(0, min(100, analysis["score"] + 50))
    
    # Cache result
    if use_cache:
        cache.set(cache_key, analysis, CACHE_TTL)
    
    return analysis


def auto_generate_seo_metadata(
    content_object: Any,
    force_regenerate: bool = False
) -> Optional[Metadata]:
    """
    Automatically generate complete SEO metadata for content object.
    
    Args:
        content_object: Django model instance
        force_regenerate: Force regeneration even if metadata exists
        
    Returns:
        Metadata instance or None on error
    """
    try:
        content_type = ContentType.objects.get_for_model(content_object)
        
        # Get or create SEOModel
        seo, created = SEOModel.objects.get_or_create(
            content_type=content_type,
            object_id=content_object.pk
        )
        
        # Check if regeneration needed
        if not created and not force_regenerate:
            try:
                metadata = seo.metadata
                if metadata and metadata.meta_title:
                    logger.debug(f"SEO metadata already exists for {content_object}")
                    return metadata
            except Metadata.DoesNotExist:
                pass
        
        # Extract content
        content_text = ""
        title = ""
        
        if hasattr(content_object, 'body'):
            content_text = content_object.body
        if hasattr(content_object, 'title'):
            title = content_object.title
        
        if not content_text:
            logger.warning(f"No content to generate SEO for {content_object}")
            return None
        
        # Compute content hash
        content_hash = _compute_content_hash(content_text)
        
        # Generate components
        keywords = extract_keywords(content_text, max_keywords=5)
        meta_title = generate_meta_title(content_text, title, keywords)
        meta_desc = generate_meta_description(content_text, title, keywords)
        
        # Get or create metadata
        metadata, _ = Metadata.objects.get_or_create(
            seo=seo,
            defaults={
                "meta_title": meta_title,
                "meta_description": meta_desc,
                "focus_keywords": keywords,
                "content_hash": content_hash,
                "ai_generated": True,
                "generated_at": timezone.now()
            }
        )
        
        # Update if forcing regeneration
        if force_regenerate:
            metadata.meta_title = meta_title
            metadata.meta_description = meta_desc
            metadata.focus_keywords = keywords
            metadata.content_hash = content_hash
            metadata.ai_generated = True
            metadata.generated_at = timezone.now()
            metadata.save()
        
        # Generate schema markup
        schema_data = {
            "title": title,
            "description": meta_desc,
            "url": getattr(content_object, 'get_absolute_url', lambda: '')(),
        }
        
        if hasattr(content_object, 'author'):
            schema_data["author"] = {
                "name": str(content_object.author),
                "url": ""
            }
        
        if hasattr(content_object, 'published_at'):
            schema_data["published_at"] = content_object.published_at
        
        schema_markup = generate_schema_markup("Article", schema_data)
        
        # Store schema
        SchemaEntry.objects.update_or_create(
            seo=seo,
            schema_type="Article",
            defaults={
                "payload": schema_markup,
                "is_active": True
            }
        )
        
        logger.info(f"Generated SEO metadata for {content_object}")
        return metadata
        
    except Exception as exc:
        logger.error(f"Failed to generate SEO metadata: {exc}", exc_info=True)
        return None


def bulk_generate_seo(queryset, batch_size: int = 50) -> Dict[str, int]:
    """
    Bulk generate SEO metadata for queryset.
    
    Args:
        queryset: Django queryset of objects
        batch_size: Number of objects to process at once
        
    Returns:
        Statistics dictionary
    """
    stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}
    
    total = queryset.count()
    stats["total"] = total
    
    logger.info(f"Starting bulk SEO generation for {total} objects")
    
    for i, obj in enumerate(queryset.iterator(chunk_size=batch_size)):
        try:
            result = auto_generate_seo_metadata(obj, force_regenerate=False)
            if result:
                stats["success"] += 1
            else:
                stats["skipped"] += 1
        except Exception as exc:
            logger.error(f"Failed to generate SEO for object {obj.pk}: {exc}")
            stats["failed"] += 1
        
        # Log progress
        if (i + 1) % batch_size == 0:
            logger.info(f"Processed {i + 1}/{total} objects")
    
    logger.info(f"Bulk SEO generation complete: {stats}")
    return stats
