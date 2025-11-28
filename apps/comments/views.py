from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone
from django.core.cache import cache
from django.db.models import F
from django.contrib.admin.views.decorators import staff_member_required

from apps.blog.models import Post
from apps.core.views import _get_site_settings_snapshot
from .models import Comment
from apps.core import ai_client
from apps.core.utils import feature_flags


@login_required
@require_POST
def add_comment(request: HttpRequest, slug: str) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    if not settings_snapshot.get("enable_blog") or not settings_snapshot.get(
        "enable_blog_comments"
    ):
        return HttpResponseBadRequest("Comments are disabled.")
    if not _has_comments_consent(request):
        return HttpResponseBadRequest("Consent required.")

    post = get_object_or_404(Post, slug=slug, is_published=True)
    body = (request.POST.get("body") or "").strip()
    if not body:
        return HttpResponseBadRequest("Comment body required.")
    if not _check_comment_rate_limit(request):
        return HttpResponseBadRequest("Too many comments, slow down.")
    Comment.objects.create(
        post=post,
        user=request.user,
        body=body,
        status=Comment.Status.APPROVED,
        is_approved=True,
    )
    return redirect("blog:post_detail", slug=slug)


@require_GET
def list_comments(request: HttpRequest, slug: str) -> JsonResponse:
    """
    JSON API for comments with pagination and sorting.
    """
    settings_snapshot = _get_site_settings_snapshot()
    if not settings_snapshot.get("enable_blog") or not settings_snapshot.get(
        "enable_blog_comments"
    ):
        return JsonResponse({"error": "comments_disabled"}, status=403)
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)

    post = get_object_or_404(Post, slug=slug, is_published=True)
    sort = request.GET.get("sort", "new")
    qs = Comment.objects.filter(
        post=post,
        status=Comment.Status.APPROVED,
        is_deleted=False,
        parent__isnull=True,
    ).prefetch_related("children")
    if sort == "old":
        qs = qs.order_by("created_at")
    elif sort == "top":
        qs = qs.order_by("-score", "-created_at")
    else:
        qs = qs.order_by("-created_at")
    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page") or 1
    page_obj = paginator.get_page(page_number)
    def serialize(comment):
        children = [
            serialize(child)
            for child in comment.children.all()
            if child.status == Comment.Status.APPROVED and not child.is_deleted
        ]
        return {
            "id": comment.id,
            "user": str(comment.user),
            "body": comment.body,
            "created_at": comment.created_at.isoformat(),
            "score": comment.score,
            "children": children,
            "metadata": comment.metadata or {},
            "status": comment.status,
        }

    payload = [serialize(c) for c in page_obj]
    return JsonResponse(
        {
            "items": payload,
            "page": page_obj.number,
            "pages": paginator.num_pages,
            "total": paginator.count,
        }
    )


@login_required
@require_POST
def add_comment_json(request: HttpRequest, slug: str) -> JsonResponse:
    """
    JSON POST endpoint for async comment submission.
    """
    settings_snapshot = _get_site_settings_snapshot()
    if not settings_snapshot.get("enable_blog") or not settings_snapshot.get(
        "enable_blog_comments"
    ):
        return JsonResponse({"error": "Comments are disabled."}, status=400)
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)
    if not _check_comment_rate_limit(request):
        return JsonResponse({"error": "rate_limited"}, status=429)
    post = get_object_or_404(Post, slug=slug, is_published=True)
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)
    body = (request.POST.get("body") or "").strip()
    if not body:
        return JsonResponse({"error": "Comment body required."}, status=400)
    parent_id = request.POST.get("parent")
    parent = None
    if parent_id:
        parent = Comment.objects.filter(pk=parent_id, post=post).first()
    meta = {}
    status = Comment.Status.PENDING
    toxicity_score = 0.0
    try:
        moderation = ai_client.moderate_text(body, request.user)
        meta["moderation"] = moderation
        toxicity_score = float(moderation.get("toxicity_score", 0.0) or 0.0)
        label = str(moderation.get("label", "low")).lower()
        if label == "high" or toxicity_score >= 0.5:
            status = Comment.Status.SPAM
        else:
            status = Comment.Status.APPROVED
    except Exception:
        status = Comment.Status.APPROVED
    is_approved = status == Comment.Status.APPROVED

    comment = Comment.objects.create(
        post=post,
        user=request.user,
        body=body,
        parent=parent,
        created_at=timezone.now(),
        is_approved=is_approved,
        status=status,
        metadata=meta,
        moderation_flags=meta,
        toxicity_score=toxicity_score,
    )
    return JsonResponse(
        {
            "ok": True,
            "id": comment.id,
            "body": comment.body,
            "user": str(comment.user),
            "created_at": comment.created_at.isoformat(),
            "metadata": meta,
            "status": status,
            "message": "Submitted for review" if status != Comment.Status.APPROVED else "Posted",
        }
    )


@login_required
@require_POST
def upvote_comment(request: HttpRequest, comment_id: int) -> JsonResponse:
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)
    if not _check_comment_rate_limit(request):
        return JsonResponse({"error": "rate_limited"}, status=429)
    comment = get_object_or_404(Comment, pk=comment_id)
    Comment.objects.filter(pk=comment.pk).update(score=F("score") + 1)
    comment.refresh_from_db()
    return JsonResponse({"ok": True, "score": comment.score})


def _check_comment_rate_limit(request: HttpRequest) -> bool:
    """
    Simple per-IP + user throttle to prevent abuse.
    """
    key_bits = []
    if getattr(request, "user", None) and request.user.is_authenticated:
        key_bits.append(f"user:{request.user.pk}")
    ip = request.META.get("REMOTE_ADDR", "anon")
    key_bits.append(f"ip:{ip}")
    key = "comments:rl:" + ":".join(key_bits)
    try:
        count = cache.get(key, 0)
        if count and int(count) >= 10:
            return False
        cache.set(key, int(count) + 1, timeout=60)
    except Exception:
        # fail open
        return True
    return True


def _has_comments_consent(request: HttpRequest) -> bool:
    consent = getattr(request, "consent_categories", {}) or {}
    if consent and not consent.get("functional", True):
        return False
    if "comments" in consent and not consent.get("comments", False):
        return False
    return True


@staff_member_required
def moderation_queue(request: HttpRequest) -> HttpResponse:
    pending = Comment.objects.filter(status=Comment.Status.PENDING, is_deleted=False).order_by("-created_at")[:50]
    recent = Comment.objects.filter(status__in=[Comment.Status.APPROVED, Comment.Status.REJECTED, Comment.Status.SPAM], is_deleted=False).order_by("-created_at")[:50]
    return render(request, "comments/moderation.html", {"pending": pending, "recent": recent})


@staff_member_required
@require_POST
def moderation_action(request: HttpRequest) -> HttpResponse:
    cid = request.POST.get("comment_id")
    action = request.POST.get("action")
    comment = get_object_or_404(Comment, pk=cid)
    if action == "approve":
        comment.status = Comment.Status.APPROVED
        comment.is_approved = True
    elif action == "reject":
        comment.status = Comment.Status.REJECTED
        comment.is_approved = False
    elif action == "spam":
        comment.status = Comment.Status.SPAM
        comment.is_approved = False
    comment.save(update_fields=["status", "is_approved"])
    return redirect("comments:moderation_queue")
