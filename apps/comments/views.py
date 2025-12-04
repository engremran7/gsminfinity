
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST
from apps.consent.decorators import consent_required
from django.utils import timezone
from django.db.models import F
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta

from apps.blog.models import Post
from apps.core.views import _get_site_settings_snapshot
from apps.core.app_service import AppService
from .models import Comment
from apps.core import ai_client
from apps.comments.services.moderation import classify_comment
from apps.core.utils import feature_flags
from apps.core.utils.ip import get_client_ip
from apps.users.services.rate_limit import allow_action


@login_required
@require_POST
@consent_required(["functional", "comments"])
def add_comment(request: HttpRequest, slug: str) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_settings = {}
    try:
        comment_api = AppService.get("comments")
        comment_settings = comment_api.get_settings() if comment_api and hasattr(comment_api, "get_settings") else {}
    except Exception:
        comment_api = None
        comment_settings = {}
    if not comment_settings.get("enable_comments", False if comment_api is None else True):
        return HttpResponseBadRequest("Comments are disabled.")
    if not blog_settings.get("enable_blog", settings_snapshot.get("enable_blog")) or not blog_settings.get(
        "enable_blog_comments", settings_snapshot.get("enable_blog_comments")
    ):
        return HttpResponseBadRequest("Comments are disabled.")
    if not _has_comments_consent(request):
        return HttpResponseForbidden("Consent required.")

    post = get_object_or_404(Post, slug=slug)
    if not post.is_live and not (request.user.is_staff or request.user == post.author):
        return HttpResponseBadRequest("Comments are disabled for this post.")
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
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_settings = {}
    try:
        comment_api = AppService.get("comments")
        comment_settings = comment_api.get_settings() if comment_api and hasattr(comment_api, "get_settings") else {}
    except Exception:
        comment_api = None
        comment_settings = {}
    if not comment_settings.get("enable_comments", False if comment_api is None else True):
        return JsonResponse({"error": "comments_disabled"}, status=403)
    if not blog_settings.get("enable_blog", settings_snapshot.get("enable_blog")) or not blog_settings.get(
        "enable_blog_comments", settings_snapshot.get("enable_blog_comments")
    ):
        return JsonResponse({"error": "comments_disabled"}, status=403)
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)

    post = get_object_or_404(Post, slug=slug)
    if not post.is_live and not (request.user.is_staff or request.user == post.author):
        return JsonResponse({"error": "comments_disabled"}, status=403)
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
            "user_id": comment.user_id,
            "body": comment.body,
            "created_at": comment.created_at.isoformat(),
            "edited_at": comment.edited_at.isoformat() if comment.edited_at else None,
            "score": comment.score,
            "children": children,
            "metadata": comment.metadata or {},
            "status": comment.status,
            "is_owner": request.user.is_authenticated and request.user.id == comment.user_id,
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
@consent_required(["functional", "comments"])
def add_comment_json(request: HttpRequest, slug: str) -> JsonResponse:
    """
    JSON POST endpoint for async comment submission.
    """
    settings_snapshot = _get_site_settings_snapshot()
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_settings = {}
    try:
        comment_api = AppService.get("comments")
        comment_settings = comment_api.get_settings() if comment_api and hasattr(comment_api, "get_settings") else {}
    except Exception:
        comment_api = None
        comment_settings = {}
    if not comment_settings.get("enable_comments", False if comment_api is None else True):
        return JsonResponse({"error": "Comments are disabled."}, status=400)
    if not blog_settings.get("enable_blog", settings_snapshot.get("enable_blog")) or not blog_settings.get(
        "enable_blog_comments", settings_snapshot.get("enable_blog_comments")
    ):
        return JsonResponse({"error": "Comments are disabled."}, status=400)
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)
    if not _check_comment_rate_limit(request):
        return JsonResponse({"error": "rate_limited"}, status=429)
    post = get_object_or_404(Post, slug=slug)
    if not post.is_live and not (request.user.is_staff or request.user == post.author):
        return JsonResponse({"error": "comments_disabled"}, status=403)
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
    # Basic language detection flag for auditing
    meta["locale"] = getattr(request, "locale", None) or request.LANGUAGE_CODE
    try:
        moderation = classify_comment(body, context=post.title)
        meta["moderation"] = {
            "label": moderation.label,
            "score": moderation.score,
            "rationale": moderation.rationale,
        }
        toxicity_score = float(moderation.score or 0.0)
        label = str(moderation.label or "pending").lower()
        if label in {"spam", "abuse"} or toxicity_score >= 0.5:
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
    msg = "Comment posted"
    if status != Comment.Status.APPROVED:
        msg = "Submitted for review" if status == Comment.Status.PENDING else "Flagged as spam"
    return JsonResponse(
        {
            "ok": True,
            "id": comment.id,
            "body": comment.body,
            "user": str(comment.user),
            "created_at": comment.created_at.isoformat(),
            "metadata": meta,
            "status": status,
            "message": msg,
            "is_owner": True,
        }
    )


@login_required
@require_POST
@consent_required(["functional", "comments"])
def upvote_comment(request: HttpRequest, comment_id: int) -> JsonResponse:
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)
    if not _check_comment_rate_limit(request):
        return JsonResponse({"error": "rate_limited"}, status=429)
    comment = get_object_or_404(Comment, pk=comment_id)
    Comment.objects.filter(pk=comment.pk).update(score=F("score") + 1)
    comment.refresh_from_db()
    return JsonResponse(
        {
            "ok": True,
            "score": comment.score,
            "status": comment.status,
            "is_deleted": comment.is_deleted,
        }
    )


@login_required
@require_POST
@consent_required(["functional", "comments"])
def report_comment(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Lightweight reporting endpoint to flag a comment for moderation.
    """
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)
    comment = get_object_or_404(Comment, pk=comment_id, is_deleted=False)
    meta = comment.moderation_metadata or {}
    reports = meta.get("reports", 0)
    meta["reports"] = reports + 1
    comment.moderation_metadata = meta
    comment.status = Comment.Status.PENDING
    comment.save(update_fields=["moderation_metadata", "status"])
    return JsonResponse({"ok": True, "status": comment.status})


@login_required
@require_POST
@consent_required(["functional", "comments"])
def edit_comment(request: HttpRequest, comment_id: int) -> JsonResponse:
    """
    Allow owners to edit their comment within a grace period; keep history.
    """
    if not _has_comments_consent(request):
        return JsonResponse({"error": "consent_required"}, status=403)

    comment = get_object_or_404(Comment, pk=comment_id, is_deleted=False)
    if comment.user_id != request.user.id and not request.user.is_staff:
        return JsonResponse({"error": "forbidden"}, status=403)

    # Grace window: 24 hours after creation unless staff
    if not request.user.is_staff and comment.created_at < timezone.now() - timedelta(hours=24):
        return JsonResponse({"error": "edit_window_expired"}, status=400)

    body = (request.POST.get("body") or "").strip()
    if not body:
        return JsonResponse({"error": "Comment body required."}, status=400)

    history = comment.metadata.get("history", []) if comment.metadata else []
    history.append(
        {
            "body": comment.body,
            "edited_at": timezone.now().isoformat(),
        }
    )
    # Keep last 5 history entries
    history = history[-5:]

    comment.body = body
    comment.edited_at = timezone.now()
    comment.metadata = comment.metadata or {}
    comment.metadata["history"] = history
    comment.save(update_fields=["body", "edited_at", "metadata"])

    return JsonResponse(
        {
            "ok": True,
            "id": comment.id,
            "body": comment.body,
            "edited_at": comment.edited_at.isoformat(),
        }
    )


def _check_comment_rate_limit(request: HttpRequest) -> bool:
    """
    Simple per-IP + user throttle to prevent abuse.
    """
    key_bits = []
    if getattr(request, "user", None) and request.user.is_authenticated:
        key_bits.append(f"user:{request.user.pk}")
    ip = get_client_ip(request) or "anon"
    key_bits.append(f"ip:{ip}")
    key = "comments:rl:" + ":".join(key_bits)
    return allow_action(key, max_attempts=10, window_seconds=60)


def _has_comments_consent(request: HttpRequest) -> bool:
    """
    Returns True only when functional consent is granted and comment consent
    (if defined) is accepted. Unknown or missing consent defaults to deny.
    """
    consent = getattr(request, "consent_categories", None)
    if not consent:
        return False
    if not consent.get("functional", False):
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


