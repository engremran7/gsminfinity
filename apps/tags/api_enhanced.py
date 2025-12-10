"""
Enterprise-grade Tag API endpoints.
REST API for all tag features including trending, suggestions, analytics, and relationships.
"""
from __future__ import annotations

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q
import json
import logging

from apps.tags.models import Tag
from apps.tags.models_enhanced import (
    TagCategory, TagTrending, TagSuggestion, TagSubscription, TagCollection
)
from apps.tags.services.tag_service import TagService

logger = logging.getLogger(__name__)


@require_GET
def search_tags_api(request: HttpRequest) -> JsonResponse:
    """
    Search tags with autocomplete.
    
    Query params:
        - q: Search query
        - limit: Max results (default: 20, max: 100)
        - category: Filter by category ID
        - curated_only: Only show curated tags (default: false)
    """
    query = request.GET.get("q", "").strip()
    limit = min(int(request.GET.get("limit", 20)), 100)
    category_id = request.GET.get("category")
    curated_only = request.GET.get("curated_only", "false").lower() == "true"
    
    # Build queryset
    qs = Tag.objects.filter(is_active=True, is_deleted=False)
    
    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(normalized_name__icontains=query) |
            Q(description__icontains=query)
        )
    
    if category_id:
        qs = qs.filter(category_id=category_id)
    
    if curated_only:
        qs = qs.filter(is_curated=True)
    
    # Order by relevance (usage + exact match boost)
    qs = qs.order_by("-usage_count", "name")[:limit]
    
    tags_data = []
    for tag in qs:
        tags_data.append({
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "usage_count": tag.usage_count,
            "is_curated": tag.is_curated,
            "is_trending": hasattr(tag, "trending_data") and tag.trending_data.exists(),
        })
    
    return JsonResponse({
        "tags": tags_data,
        "count": len(tags_data)
    })


@require_GET
def list_tags_api(request: HttpRequest) -> JsonResponse:
    """
    List all tags with pagination and filtering.
    
    Query params:
        - page: Page number
        - per_page: Items per page (default: 50, max: 100)
        - category: Filter by category ID
        - sort: usage, name, trending (default: usage)
        - min_usage: Minimum usage count
    """
    # Build queryset
    qs = Tag.objects.filter(is_active=True, is_deleted=False)
    
    # Filter by category
    category_id = request.GET.get("category")
    if category_id:
        qs = qs.filter(category_id=category_id)
    
    # Filter by minimum usage
    min_usage = request.GET.get("min_usage")
    if min_usage:
        qs = qs.filter(usage_count__gte=int(min_usage))
    
    # Sort
    sort_by = request.GET.get("sort", "usage")
    if sort_by == "name":
        qs = qs.order_by("name")
    elif sort_by == "trending":
        # Join with trending data
        from apps.tags.models_enhanced import TagTrending
        trending_ids = TagTrending.objects.filter(
            period="daily"
        ).order_by("rank").values_list("tag_id", flat=True)[:100]
        qs = qs.filter(id__in=trending_ids)
    else:  # usage
        qs = qs.order_by("-usage_count", "name")
    
    # Paginate
    per_page = min(int(request.GET.get("per_page", 50)), 100)
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page", 1)
    page = paginator.get_page(page_number)
    
    # Serialize
    tags_data = []
    for tag in page:
        tags_data.append({
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "usage_count": tag.usage_count,
            "is_curated": tag.is_curated,
        })
    
    return JsonResponse({
        "tags": tags_data,
        "pagination": {
            "page": page.number,
            "per_page": per_page,
            "total_pages": paginator.num_pages,
            "total_tags": paginator.count,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        }
    })


@require_GET
def get_tag_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Get detailed tag information including stats and relationships.
    """
    tag = get_object_or_404(Tag, slug=slug, is_deleted=False)
    
    # Get comprehensive stats via service
    service = TagService()
    try:
        stats = service.get_tag_stats(tag)
    except Exception as e:
        logger.error(f"Failed to get tag stats: {e}")
        stats = {}
    
    # Check if user is subscribed
    is_subscribed = False
    if request.user.is_authenticated:
        is_subscribed = TagSubscription.objects.filter(
            tag=tag,
            user=request.user,
            is_active=True
        ).exists()
    
    return JsonResponse({
        "tag": {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "usage_count": tag.usage_count,
            "is_curated": tag.is_curated,
            "parent": {
                "id": tag.parent.id,
                "name": tag.parent.name,
                "slug": tag.parent.slug,
            } if tag.parent else None,
        },
        "stats": stats,
        "is_subscribed": is_subscribed,
    })


@require_GET
def get_trending_tags_api(request: HttpRequest) -> JsonResponse:
    """
    Get trending tags for specified period.
    
    Query params:
        - period: hourly, daily, weekly, monthly (default: daily)
        - limit: Max results (default: 10, max: 50)
    """
    period = request.GET.get("period", "daily")
    limit = min(int(request.GET.get("limit", 10)), 50)
    
    # Validate period
    valid_periods = ["hourly", "daily", "weekly", "monthly"]
    if period not in valid_periods:
        return JsonResponse({"error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"}, status=400)
    
    # Get trending tags via service
    service = TagService()
    try:
        tags = service.get_trending_tags(period, limit)
    except Exception as e:
        logger.error(f"Failed to get trending tags: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    # Get trending data
    trending_data = {}
    from apps.tags.models_enhanced import TagTrending
    for trending in TagTrending.objects.filter(
        tag__in=tags,
        period=period
    ):
        trending_data[trending.tag_id] = {
            "rank": trending.rank,
            "growth_rate": trending.growth_rate,
            "trending_score": trending.trending_score,
            "usage_count": trending.usage_count,
        }
    
    tags_data = []
    for tag in tags:
        tag_data = {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
            "usage_count": tag.usage_count,
        }
        if tag.id in trending_data:
            tag_data["trending"] = trending_data[tag.id]
        tags_data.append(tag_data)
    
    return JsonResponse({
        "period": period,
        "tags": tags_data
    })


@require_GET
def get_related_tags_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Get tags related to specified tag.
    
    Query params:
        - type: synonym, related, broader, narrower (optional)
        - limit: Max results (default: 10, max: 50)
    """
    tag = get_object_or_404(Tag, slug=slug, is_deleted=False)
    
    relationship_type = request.GET.get("type")
    limit = min(int(request.GET.get("limit", 10)), 50)
    
    # Get related tags via service
    service = TagService()
    try:
        related = service.get_related_tags(tag, relationship_type, limit=limit)
    except Exception as e:
        logger.error(f"Failed to get related tags: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "related_tags": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "usage_count": t.usage_count,
            }
            for t in related
        ]
    })


@login_required
@require_POST
def suggest_tags_for_content_api(request: HttpRequest) -> JsonResponse:
    """
    Get AI-powered tag suggestions for content.
    
    POST data:
        - content: Content text
        - title: Optional title
        - existing_tags: Optional list of existing tag names
        - max_suggestions: Max suggestions (default: 5, max: 10)
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    content = data.get("content", "")
    title = data.get("title", "")
    existing_tags = data.get("existing_tags", [])
    max_suggestions = min(int(data.get("max_suggestions", 5)), 10)
    
    if not content:
        return JsonResponse({"error": "content required"}, status=400)
    
    # Get suggestions via service
    service = TagService()
    try:
        suggestions = service.suggest_tags_for_content(
            content=content,
            title=title,
            existing_tags=existing_tags,
            max_suggestions=max_suggestions
        )
    except Exception as e:
        logger.error(f"Failed to get tag suggestions: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "suggestions": suggestions
    })


@login_required
@require_POST
def create_tag_suggestion_api(request: HttpRequest) -> JsonResponse:
    """
    Submit new tag suggestion for review.
    
    POST data:
        - name: Suggested tag name
        - description: Optional description
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    name = data.get("name", "").strip()
    description = data.get("description", "")
    
    if not name:
        return JsonResponse({"error": "name required"}, status=400)
    
    # Create suggestion via service
    service = TagService()
    try:
        suggestion = service.create_tag_suggestion(
            suggested_name=name,
            suggested_by=request.user,
            description=description
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Failed to create tag suggestion: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "suggestion": {
            "id": suggestion.id,
            "name": suggestion.suggested_name,
            "status": suggestion.status,
            "created_at": suggestion.created_at.isoformat(),
        }
    }, status=201)


@login_required
@require_POST
def subscribe_to_tag_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Subscribe to tag notifications.
    
    POST data:
        - frequency: instant, daily, weekly, never (default: instant)
    """
    tag = get_object_or_404(Tag, slug=slug, is_deleted=False)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    
    frequency = data.get("frequency", "instant")
    valid_frequencies = ["instant", "daily", "weekly", "never"]
    if frequency not in valid_frequencies:
        return JsonResponse({"error": f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}"}, status=400)
    
    # Subscribe via service
    service = TagService()
    try:
        subscription = service.subscribe_to_tag(tag, request.user, frequency)
    except Exception as e:
        logger.error(f"Failed to subscribe: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "subscribed": True,
        "frequency": frequency
    })


@login_required
@require_POST
def unsubscribe_from_tag_api(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Unsubscribe from tag notifications.
    """
    tag = get_object_or_404(Tag, slug=slug, is_deleted=False)
    
    # Unsubscribe via service
    service = TagService()
    try:
        success = service.unsubscribe_from_tag(tag, request.user)
    except Exception as e:
        logger.error(f"Failed to unsubscribe: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": success,
        "subscribed": False
    })


@staff_member_required
@require_POST
def approve_tag_suggestion_api(request: HttpRequest, suggestion_id: int) -> JsonResponse:
    """
    Approve tag suggestion and create tag (staff only).
    """
    suggestion = get_object_or_404(TagSuggestion, id=suggestion_id)
    
    if suggestion.status != TagSuggestion.Status.PENDING:
        return JsonResponse({"error": "Suggestion already reviewed"}, status=400)
    
    # Approve via service
    service = TagService()
    try:
        tag = service.approve_tag_suggestion(suggestion, request.user)
    except Exception as e:
        logger.error(f"Failed to approve suggestion: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "tag": {
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
        }
    })


@staff_member_required
@require_POST
def merge_tags_api(request: HttpRequest) -> JsonResponse:
    """
    Merge source tag into target tag (staff only).
    
    POST data:
        - source_slug: Source tag slug
        - target_slug: Target tag slug
        - reason: Optional reason
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    source_slug = data.get("source_slug")
    target_slug = data.get("target_slug")
    
    if not source_slug or not target_slug:
        return JsonResponse({"error": "source_slug and target_slug required"}, status=400)
    
    source_tag = get_object_or_404(Tag, slug=source_slug)
    target_tag = get_object_or_404(Tag, slug=target_slug)
    
    reason = data.get("reason", "")
    
    # Merge via service
    service = TagService()
    try:
        merge = service.merge_tags(source_tag, target_tag, request.user, reason)
    except Exception as e:
        logger.error(f"Failed to merge tags: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "merge": {
            "id": merge.id,
            "source_name": merge.source_tag_name,
            "target_name": merge.target_tag.name,
            "items_migrated": merge.items_migrated,
        }
    })


@require_GET
def get_tag_categories_api(request: HttpRequest) -> JsonResponse:
    """
    List all tag categories.
    """
    categories = TagCategory.objects.filter(
        is_active=True,
        is_deleted=False
    ).order_by("display_order", "name")
    
    return JsonResponse({
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "description": cat.description,
                "color": cat.color,
                "icon": cat.icon,
            }
            for cat in categories
        ]
    })


@login_required
@require_GET
def get_user_tag_subscriptions_api(request: HttpRequest) -> JsonResponse:
    """
    Get user's tag subscriptions.
    """
    subscriptions = TagSubscription.objects.filter(
        user=request.user,
        is_active=True
    ).select_related("tag").order_by("-created_at")
    
    return JsonResponse({
        "subscriptions": [
            {
                "tag": {
                    "id": sub.tag.id,
                    "name": sub.tag.name,
                    "slug": sub.tag.slug,
                },
                "frequency": sub.notification_frequency,
                "subscribed_at": sub.created_at.isoformat(),
            }
            for sub in subscriptions
        ]
    })


@login_required
@require_POST
def create_tag_collection_api(request: HttpRequest) -> JsonResponse:
    """
    Create new tag collection.
    
    POST data:
        - name: Collection name
        - description: Optional description
        - tag_slugs: List of tag slugs
        - is_public: Boolean (default: false)
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    name = data.get("name", "").strip()
    description = data.get("description", "")
    tag_slugs = data.get("tag_slugs", [])
    is_public = data.get("is_public", False)
    
    if not name:
        return JsonResponse({"error": "name required"}, status=400)
    
    # Get tags
    tags = Tag.objects.filter(slug__in=tag_slugs)
    
    # Create collection
    from django.utils.text import slugify
    collection = TagCollection.objects.create(
        name=name,
        slug=slugify(name),
        description=description,
        owner=request.user,
        is_public=is_public
    )
    
    # Add tags
    from apps.tags.models_enhanced import TagCollectionItem
    for order, tag in enumerate(tags):
        TagCollectionItem.objects.create(
            collection=collection,
            tag=tag,
            order=order
        )
    
    return JsonResponse({
        "success": True,
        "collection": {
            "id": collection.id,
            "name": collection.name,
            "slug": collection.slug,
            "tag_count": tags.count(),
        }
    }, status=201)
