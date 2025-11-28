from __future__ import annotations

from django.http import JsonResponse, Http404, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from .models import Tag
from apps.blog.models import Post, PostStatus
from django.template.loader import render_to_string
from django.utils import timezone
from apps.core import ai_client


@require_GET
def search(request):
    """
    Tag autocomplete/search endpoint.
    """
    q = request.GET.get("q", "").strip()
    qs = Tag.objects.filter(is_active=True, is_deleted=False)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(normalized_name__icontains=q))
    qs = qs.order_by("-usage_count", "name")[:20]
    items = [
        {
            "name": t.name,
            "slug": t.slug,
            "usage_count": t.usage_count,
            "synonyms": t.synonyms,
            "description": t.description,
        }
        for t in qs
    ]
    return JsonResponse({"items": items})


def tag_list(request: HttpRequest) -> HttpResponse:
    tags = Tag.objects.filter(is_active=True, is_deleted=False).order_by("-usage_count", "name")
    return render(request, "tags/list.html", {"tags": tags})


def tag_detail(request: HttpRequest, slug: str) -> HttpResponse:
    tag = get_object_or_404(Tag, slug=slug, is_deleted=False)
    now_ts = timezone.now()
    posts = (
        Post.objects.filter(tags=tag, status=PostStatus.PUBLISHED, publish_at__lte=now_ts)
        .select_related("author", "category")
        .prefetch_related("tags")
        .order_by("-published_at")
    )
    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    trending_tags = Tag.objects.order_by("-usage_count")[:10]
    trending_tags = trending_tags.filter(is_deleted=False)
    latest = (
        Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=now_ts)
        .order_by("-published_at")[:5]
    )
    trending_tags_html = render_to_string(
        "components/tag_badges.html", {"tags": trending_tags}
    )
    latest_widget_html = render_to_string(
        "blog/partials/latest_widget.html", {"posts": latest}
    )
    return render(
        request,
        "tags/detail.html",
        {
            "tag": tag,
            "posts": page_obj.object_list,
            "page_obj": page_obj,
            "trending_tags_html": trending_tags_html,
            "latest_widget_html": latest_widget_html,
        },
    )


@login_required
@require_POST
def merge_tags(request: HttpRequest) -> JsonResponse:
    """
    Simple admin/staff merge: expects source_slug -> target_slug, reassign posts, delete source.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    source_slug = request.POST.get("source")
    target_slug = request.POST.get("target")
    if not source_slug or not target_slug or source_slug == target_slug:
        return JsonResponse({"ok": False, "error": "invalid"}, status=400)
    source = get_object_or_404(Tag, slug=source_slug, is_deleted=False)
    target = get_object_or_404(Tag, slug=target_slug, is_deleted=False)
    posts = Post.objects.filter(tags=source)
    for p in posts:
        p.tags.add(target)
        p.tags.remove(source)
    source.is_deleted = True
    source.is_active = False
    source.save(update_fields=["is_deleted", "is_active"])
    target.usage_count = target.posts.count()
    target.save(update_fields=["usage_count"])
    return JsonResponse({"ok": True, "merged": source_slug, "into": target_slug})


def tag_analytics(request: HttpRequest) -> HttpResponse:
    tags = Tag.objects.order_by("-usage_count", "name")[:50]
    data = [{"name": t.name, "usage": t.usage_count} for t in tags]
    return JsonResponse({"items": data})


@require_POST
def suggest_tags(request: HttpRequest) -> JsonResponse:
    """
    AI tag suggestions endpoint; requires explicit acceptance on the client.
    """
    text = (request.POST.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "empty"}, status=400)
    try:
        suggestions = ai_client.suggest_tags(text, request.user if request.user.is_authenticated else None)
        return JsonResponse({"ok": True, "suggestions": suggestions})
    except Exception:
        return JsonResponse({"ok": False, "error": "failed"}, status=500)
