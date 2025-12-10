"""
Enterprise-grade Comment API endpoints.
REST API for all comment features including reactions, voting, threading, and moderation.
"""
from __future__ import annotations

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Count, Q, Prefetch
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from apps.comments.models import Comment
from apps.comments.models_enhanced import (
    CommentReaction, CommentVote, CommentFlag, CommentAward
)
from apps.comments.services.comment_service import CommentService

logger = logging.getLogger(__name__)


def _get_content_object(content_type_id: int, object_id: int):
    """Get content object from content type and ID."""
    try:
        content_type = ContentType.objects.get(id=content_type_id)
        return content_type.get_object_for_this_type(id=object_id)
    except (ContentType.DoesNotExist, Exception):
        return None


@require_GET
def list_comments_api(request: HttpRequest) -> JsonResponse:
    """
    List comments with filtering, sorting, and pagination.
    
    Query params:
        - content_type: ContentType ID
        - object_id: Object ID
        - sort: score, date, votes, reactions (default: date)
        - page: Page number
        - per_page: Items per page (default: 20, max: 100)
        - status: pending, approved, rejected (default: approved)
        - parent: Filter by parent comment ID (null for root)
    """
    # Get content object
    content_type_id = request.GET.get("content_type")
    object_id = request.GET.get("object_id")
    
    if not content_type_id or not object_id:
        return JsonResponse({"error": "content_type and object_id required"}, status=400)
    
    # Build queryset
    qs = Comment.objects.filter(
        content_type_id=content_type_id,
        object_id=object_id,
        is_deleted=False
    ).select_related(
        "user", "parent", "analytics"
    ).prefetch_related(
        "reactions", "votes", "awards"
    )
    
    # Filter by status
    status = request.GET.get("status", "approved")
    if status == "all" and request.user.is_staff:
        pass  # Show all
    else:
        qs = qs.filter(status=Comment.Status.APPROVED)
    
    # Filter by parent
    parent_id = request.GET.get("parent")
    if parent_id == "null":
        qs = qs.filter(parent__isnull=True)
    elif parent_id:
        qs = qs.filter(parent_id=parent_id)
    
    # Sort
    sort_by = request.GET.get("sort", "date")
    if sort_by == "score":
        qs = qs.order_by("-score", "-created_at")
    elif sort_by == "votes":
        qs = qs.annotate(
            vote_count=Count("votes")
        ).order_by("-vote_count", "-created_at")
    elif sort_by == "reactions":
        qs = qs.annotate(
            reaction_count=Count("reactions")
        ).order_by("-reaction_count", "-created_at")
    else:  # date
        qs = qs.order_by("-created_at")
    
    # Paginate
    per_page = min(int(request.GET.get("per_page", 20)), 100)
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get("page", 1)
    page = paginator.get_page(page_number)
    
    # Serialize
    comments_data = []
    for comment in page:
        # Get user's reaction/vote if authenticated
        user_reaction = None
        user_vote = None
        if request.user.is_authenticated:
            try:
                reaction = comment.reactions.get(user=request.user)
                user_reaction = reaction.reaction_type
            except CommentReaction.DoesNotExist:
                pass
            
            try:
                vote = comment.votes.get(user=request.user)
                user_vote = vote.vote
            except CommentVote.DoesNotExist:
                pass
        
        # Reaction counts
        reactions_summary = {}
        for reaction in comment.reactions.all():
            reactions_summary[reaction.reaction_type] = reactions_summary.get(reaction.reaction_type, 0) + 1
        
        comments_data.append({
            "id": comment.id,
            "body": comment.body,
            "user": {
                "id": comment.user.id,
                "username": comment.user.username,
            },
            "parent_id": comment.parent_id,
            "status": comment.status,
            "score": comment.score,
            "created_at": comment.created_at.isoformat(),
            "edited_at": comment.edited_at.isoformat() if comment.edited_at else None,
            "analytics": {
                "upvotes": comment.analytics.upvotes,
                "downvotes": comment.analytics.downvotes,
                "net_votes": comment.analytics.net_votes,
                "reaction_count": comment.analytics.reaction_count,
                "reply_count": comment.analytics.reply_count,
                "engagement_score": comment.analytics.engagement_score,
            } if hasattr(comment, "analytics") else {},
            "reactions": reactions_summary,
            "user_reaction": user_reaction,
            "user_vote": user_vote,
            "awards": [
                {"type": award.award_type, "created_at": award.created_at.isoformat()}
                for award in comment.awards.all()
            ],
            "has_replies": comment.children.filter(is_deleted=False).exists(),
        })
    
    return JsonResponse({
        "comments": comments_data,
        "pagination": {
            "page": page.number,
            "per_page": per_page,
            "total_pages": paginator.num_pages,
            "total_comments": paginator.count,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        }
    })


@login_required
@require_POST
def create_comment_api(request: HttpRequest) -> JsonResponse:
    """
    Create new comment.
    
    POST data:
        - content_type: ContentType ID
        - object_id: Object ID
        - body: Comment text
        - parent: Optional parent comment ID
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Validate required fields
    content_type_id = data.get("content_type")
    object_id = data.get("object_id")
    body = data.get("body", "").strip()
    
    if not all([content_type_id, object_id, body]):
        return JsonResponse({"error": "content_type, object_id, and body required"}, status=400)
    
    # Get content object
    content_object = _get_content_object(content_type_id, object_id)
    if not content_object:
        return JsonResponse({"error": "Invalid content object"}, status=404)
    
    # Get parent if specified
    parent = None
    parent_id = data.get("parent")
    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id)
    
    # Create comment via service
    service = CommentService()
    try:
        comment = service.create_comment(
            content_object=content_object,
            user=request.user,
            body=body,
            parent=parent,
            auto_approve=request.user.is_staff  # Auto-approve staff
        )
    except Exception as e:
        logger.error(f"Failed to create comment: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "comment": {
            "id": comment.id,
            "body": comment.body,
            "status": comment.status,
            "created_at": comment.created_at.isoformat(),
        }
    }, status=201)


@login_required
@require_POST
def react_to_comment_api(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Add or update reaction to comment.
    
    POST data:
        - reaction_type: like, love, insightful, funny, celebrate, support, curious, disagree
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    reaction_type = data.get("reaction_type")
    if not reaction_type:
        return JsonResponse({"error": "reaction_type required"}, status=400)
    
    # Validate reaction type
    valid_types = [choice[0] for choice in CommentReaction.ReactionType.choices]
    if reaction_type not in valid_types:
        return JsonResponse({"error": f"Invalid reaction_type. Must be one of: {', '.join(valid_types)}"}, status=400)
    
    # Add reaction via service
    service = CommentService()
    try:
        reaction = service.add_reaction(comment, request.user, reaction_type)
    except Exception as e:
        logger.error(f"Failed to add reaction: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "reaction": {
            "id": reaction.id,
            "reaction_type": reaction.reaction_type,
            "created_at": reaction.created_at.isoformat(),
        }
    })


@login_required
@require_POST
def vote_comment_api(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Vote on comment (upvote/downvote).
    
    POST data:
        - vote: 1 for upvote, -1 for downvote
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    vote = data.get("vote")
    if vote not in [1, -1]:
        return JsonResponse({"error": "vote must be 1 or -1"}, status=400)
    
    # Vote via service
    service = CommentService()
    try:
        vote_obj = service.vote_comment(comment, request.user, vote)
    except Exception as e:
        logger.error(f"Failed to vote: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    # Get updated stats
    comment.refresh_from_db()
    
    return JsonResponse({
        "success": True,
        "vote": vote,
        "score": comment.score,
        "analytics": {
            "upvotes": comment.analytics.upvotes,
            "downvotes": comment.analytics.downvotes,
            "net_votes": comment.analytics.net_votes,
        }
    })


@login_required
@require_POST
def flag_comment_api(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Flag comment for moderation.
    
    POST data:
        - reason: spam, harassment, hate_speech, off_topic, misinformation, nsfw, other
        - details: Optional additional details
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    reason = data.get("reason")
    if not reason:
        return JsonResponse({"error": "reason required"}, status=400)
    
    # Validate reason
    valid_reasons = [choice[0] for choice in CommentFlag.FlagReason.choices]
    if reason not in valid_reasons:
        return JsonResponse({"error": f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"}, status=400)
    
    details = data.get("details", "")
    
    # Flag via service
    service = CommentService()
    try:
        flag = service.flag_comment(comment, request.user, reason, details)
    except Exception as e:
        logger.error(f"Failed to flag comment: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "message": "Comment flagged for review"
    })


@login_required
@require_POST
def bookmark_comment_api(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Bookmark comment.
    
    POST data:
        - notes: Optional personal notes
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    
    notes = data.get("notes", "")
    
    # Bookmark via service
    service = CommentService()
    try:
        bookmark = service.bookmark_comment(comment, request.user, notes)
    except Exception as e:
        logger.error(f"Failed to bookmark: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "bookmarked": True
    })


@staff_member_required
@require_POST
def moderate_comment_api(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Moderate comment (staff only).
    
    POST data:
        - action: approve, reject, delete, spam
        - reason: Optional reason
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    action = data.get("action")
    if not action:
        return JsonResponse({"error": "action required"}, status=400)
    
    valid_actions = ["approve", "reject", "delete", "spam"]
    if action not in valid_actions:
        return JsonResponse({"error": f"Invalid action. Must be one of: {', '.join(valid_actions)}"}, status=400)
    
    reason = data.get("reason", "")
    
    # Moderate via service
    service = CommentService()
    try:
        mod_action = service.moderate_comment(
            comment, action, request.user, reason
        )
    except Exception as e:
        logger.error(f"Failed to moderate: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "success": True,
        "action": action,
        "status": comment.status
    })


@require_GET
def get_comment_thread_api(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Get full comment thread starting from root comment.
    
    Query params:
        - max_depth: Maximum nesting depth (default: 10)
        - sort: score, date, votes (default: score)
    """
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Get root comment
    root = comment
    while root.parent:
        root = root.parent
    
    max_depth = int(request.GET.get("max_depth", 10))
    sort_by = request.GET.get("sort", "score")
    
    # Get thread via service
    service = CommentService()
    try:
        thread = service.get_comment_thread(root, max_depth, sort_by)
    except Exception as e:
        logger.error(f"Failed to get thread: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "thread": _serialize_thread(thread)
    })


def _serialize_thread(thread_node: dict) -> dict:
    """Recursively serialize thread structure."""
    comment = thread_node["comment"]
    
    return {
        "id": comment.id,
        "body": comment.body,
        "user": {
            "id": comment.user.id,
            "username": comment.user.username,
        },
        "score": comment.score,
        "created_at": comment.created_at.isoformat(),
        "depth": thread_node["depth"],
        "replies": [
            _serialize_thread(reply)
            for reply in thread_node.get("replies", [])
        ]
    }


@require_GET
def get_top_comments_api(request: HttpRequest) -> JsonResponse:
    """
    Get top comments by engagement.
    
    Query params:
        - content_type: ContentType ID
        - object_id: Object ID
        - period: all, day, week, month (default: all)
        - limit: Number of results (default: 10, max: 50)
    """
    content_type_id = request.GET.get("content_type")
    object_id = request.GET.get("object_id")
    
    if not content_type_id or not object_id:
        return JsonResponse({"error": "content_type and object_id required"}, status=400)
    
    content_object = _get_content_object(content_type_id, object_id)
    if not content_object:
        return JsonResponse({"error": "Invalid content object"}, status=404)
    
    period = request.GET.get("period", "all")
    limit = min(int(request.GET.get("limit", 10)), 50)
    
    # Get top comments via service
    service = CommentService()
    try:
        comments = service.get_top_comments(content_object, limit, period)
    except Exception as e:
        logger.error(f"Failed to get top comments: {e}")
        return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({
        "comments": [
            {
                "id": c.id,
                "body": c.body,
                "user": {
                    "id": c.user.id,
                    "username": c.user.username,
                },
                "score": c.score,
                "engagement_score": c.analytics.engagement_score,
                "created_at": c.created_at.isoformat(),
            }
            for c in comments
        ]
    })
