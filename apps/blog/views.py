from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from django.template.loader import render_to_string
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.core.views import _get_site_settings_snapshot
from .forms import PostForm
from .models import Post, PostStatus, Category, PostDraft, PostRevision
from apps.tags.models import Tag
from apps.seo.models import SEOModel, Metadata
from apps.core.utils import feature_flags
from apps.users.models import CustomUser


def _sync_tag_usage(tags_qs):
    for tag in tags_qs:
        try:
            count = tag.posts.filter(status=PostStatus.PUBLISHED).count()
            if tag.usage_count != count:
                tag.usage_count = count
                tag.save(update_fields=["usage_count"])
        except Exception:
            continue


def _ensure_post_seo(post: Post, request: HttpRequest | None = None):
    """
    Ensure SEO metadata/linkable entry for a post when SEO is enabled.
    """
    if not feature_flags.seo_enabled():
        return
    try:
        ct = ContentType.objects.get_for_model(Post)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=post.pk)
        meta, _ = Metadata.objects.get_or_create(seo=seo_obj)
        if not meta.meta_title:
            meta.meta_title = post.seo_title or post.title
        if not meta.meta_description:
            meta.meta_description = post.seo_description or post.summary[:320]
        if not meta.canonical_url and request:
            meta.canonical_url = request.build_absolute_uri()
        meta.save()
        # Register linkable entity for internal linking
        from apps.seo.services.internal_linking.engine import refresh_linkable_entity

        refresh_linkable_entity(
            post,
            title=post.title,
            url=post.get_absolute_url(),
            keywords=",".join(post.tags.values_list("name", flat=True)),
        )
    except Exception:
        # Defensive: SEO failures should not block blog rendering
        return


def post_list(request: HttpRequest) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    blog_enabled = settings_snapshot.get("enable_blog", True)
    if not blog_enabled and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Blog is disabled.")
    allow_user_posts = settings_snapshot.get("allow_user_blog_posts", False)
    allow_user_bounties = settings_snapshot.get("allow_user_bounty_posts", False)

    now_ts = timezone.now()
    posts = Post.objects.filter(
        status=PostStatus.PUBLISHED, publish_at__lte=now_ts
    ).select_related("author", "category")
    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()
    category_slug = request.GET.get("category", "").strip()
    author = request.GET.get("author", "").strip()

    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(summary__icontains=q))
    if tag:
        posts = posts.filter(tags__slug=tag)
    if category_slug:
        posts = posts.filter(category__slug=category_slug)
    if author:
        posts = posts.filter(author__username=author)

    posts = posts.prefetch_related("tags")
    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    # Precompute display strings to keep templates simple and avoid filter gymnastics.
    for p in page_obj:
        published = p.published_at.strftime("%b %d, %Y") if p.published_at else "Draft"
        p.meta_text = f"By {p.author} · {published}"

    trending_tags = Tag.objects.order_by("-usage_count")[:10]
    trending_posts = list(
        Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=now_ts)
        .select_related("author")
        .order_by("-featured", "-published_at")[:5]
    )
    if not trending_posts:
        trending_posts = list(
            Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=now_ts)
            .select_related("author")
            .order_by("-published_at")[:5]
        )
    latest_posts = (
        Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=now_ts)
        .order_by("-published_at")[:5]
    )
    bounty_posts = (
        Post.objects.filter(
            status=PostStatus.PUBLISHED, publish_at__lte=now_ts, tags__slug="bounty"
        )
        .distinct()
        .order_by("-published_at")[:5]
    )

    context = {
        "posts": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "trending_tags": trending_tags,
        "trending_posts": trending_posts,
        "latest_posts": latest_posts,
        "bounty_posts": bounty_posts,
        "allow_user_posts": allow_user_posts,
    }
    return render(request, "blog/post_list.html", context)


def post_detail(request: HttpRequest, slug: str) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    blog_enabled = settings_snapshot.get("enable_blog", True)
    if not blog_enabled and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Blog is disabled.")
    allow_user_posts = settings_snapshot.get("allow_user_blog_posts", False)
    allow_user_bounties = settings_snapshot.get("allow_user_bounty_posts", False)

    post = get_object_or_404(
        Post.objects.select_related("author", "category").prefetch_related("tags"),
        slug=slug,
    )
    if not post.is_live and not (request.user.is_staff or request.user == post.author):
        raise Http404("Post not published.")
    related = Post.objects.filter(
        tags__in=post.tags.all(),
        status=PostStatus.PUBLISHED,
        publish_at__lte=timezone.now(),
    ).exclude(pk=post.pk).distinct().order_by("-published_at")[:4]
    related_widget_html = render_to_string(
        "blog/partials/related_widget.html", {"posts": related}
    )
    trending_tags = Tag.objects.order_by("-usage_count")[:10]
    trending_posts = list(
        Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=timezone.now())
        .select_related("author")
        .order_by("-featured", "-published_at")[:5]
    )
    if not trending_posts:
        trending_posts = list(
            Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=timezone.now())
            .select_related("author")
            .order_by("-published_at")[:5]
        )
    bounty_posts = (
        Post.objects.filter(
            status=PostStatus.PUBLISHED, publish_at__lte=timezone.now(), tags__slug="bounty"
        )
        .distinct()
        .order_by("-published_at")[:5]
    )
    _ensure_post_seo(post, request)

    return render(
        request,
        "blog/post_detail.html",
        {
            "post": post,
            "related_widget_html": related_widget_html,
            "trending_tags": trending_tags,
            "trending_posts": trending_posts,
            "bounty_posts": bounty_posts,
            "allow_user_posts": allow_user_posts,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def post_create(request: HttpRequest) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    blog_enabled = settings_snapshot.get("enable_blog", True)
    if not blog_enabled and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Blog is disabled.")

    allow_user_posts = settings_snapshot.get("allow_user_blog_posts", False)
    # RBAC: allow staff, editors, authors; optionally allow authenticated users if toggle enabled.
    allowed = (
        request.user.is_staff
        or request.user.is_superuser
        or getattr(request.user, "has_role", lambda *r: False)(
            CustomUser.Roles.EDITOR, CustomUser.Roles.AUTHOR
        )
    )
    if not allowed and not (allow_user_posts and request.user.is_authenticated):
        raise Http404()

    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            # Community bounty guardrails
            if not allow_user_bounties and not allowed:
                tags_qs = form.cleaned_data.get("tags")
                try:
                    if tags_qs and tags_qs.filter(slug="bounty").exists():
                        form.add_error(
                            "tags",
                            "Bounty posts are restricted by admin settings.",
                        )
                        return render(request, "blog/post_form.html", {"form": form})
                except Exception:
                    pass
            post = form.save(commit=False)
            post.author = request.user
            with transaction.atomic():
                post.save()
                form.save_m2m()
                _sync_tag_usage(post.tags.all())
                _ensure_post_seo(post, request)
                PostRevision.objects.create(
                    post=post,
                    user=request.user,
                    snapshot={
                        "title": post.title,
                        "summary": post.summary,
                        "body": post.body,
                        "tags": list(post.tags.values_list("slug", flat=True)),
                        "status": post.status,
                    },
                )
            messages.success(request, "Post saved.")
            return redirect("blog:post_detail", slug=post.slug)
    else:
        form = PostForm()
    return render(request, "blog/post_form.html", {"form": form})


def api_posts(request: HttpRequest) -> JsonResponse:
    """
    Lightweight JSON listing for widgets/search.
    """
    posts = Post.objects.filter(
        status=PostStatus.PUBLISHED, publish_at__lte=timezone.now()
    )
    q = request.GET.get("q", "").strip()
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(summary__icontains=q))
    posts = posts.select_related("author").order_by("-published_at")[:20]
    items = [
        {
            "title": p.title,
            "slug": p.slug,
            "author": str(p.author),
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]
    return JsonResponse({"items": items})


def api_related(request: HttpRequest, slug: str) -> JsonResponse:
    post = get_object_or_404(Post, slug=slug, status=PostStatus.PUBLISHED, publish_at__lte=timezone.now())
    related = (
        Post.objects.filter(tags__in=post.tags.all(), status=PostStatus.PUBLISHED, publish_at__lte=timezone.now())
        .exclude(pk=post.pk)
        .distinct()
        .order_by("-published_at")[:5]
    )
    items = [{"title": p.title, "slug": p.slug} for p in related]
    return JsonResponse({"items": items})


@login_required
@require_POST
def post_autosave(request: HttpRequest) -> JsonResponse:
    """
    Autosave stub for editor. Uses cache to persist the last payload per-user for 10 minutes.
    """
    post_id = request.POST.get("post_id")
    data = {
        "title": request.POST.get("title", ""),
        "summary": request.POST.get("summary", ""),
        "body": request.POST.get("body", ""),
        "tags": request.POST.getlist("tags"),
        "updated_at": timezone.now().isoformat(),
    }
    draft, _ = PostDraft.objects.update_or_create(
        user=request.user,
        post_id=post_id or None,
        defaults={"data": data},
    )
    return JsonResponse({"ok": True, "message": "Autosave stored", "draft_id": draft.id, "data": data})


@login_required
@require_POST
def post_preview(request: HttpRequest) -> JsonResponse:
    """
    Preview stub: echoes body/summary; replace with markdown rendering as needed.
    """
    body = request.POST.get("body", "")
    summary = request.POST.get("summary", "")
    rendered_body = body
    try:
        import markdown

        rendered_body = markdown.markdown(body, extensions=["fenced_code", "tables"])
    except Exception:
        pass
    return JsonResponse({"ok": True, "body": rendered_body, "summary": summary})


def widget_trending_tags(request: HttpRequest) -> JsonResponse:
    tags = Tag.objects.order_by("-usage_count", "name")[:10]
    items = [{"name": t.name, "slug": t.slug, "usage_count": t.usage_count} for t in tags]
    return JsonResponse({"items": items})


def widget_latest_posts(request: HttpRequest) -> JsonResponse:
    posts = (
        Post.objects.filter(status=PostStatus.PUBLISHED)
        .select_related("author")
        .order_by("-published_at")[:5]
    )
    items = [
        {
            "title": p.title,
            "slug": p.slug,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]
    return JsonResponse({"items": items})


def widget_top_posts(request: HttpRequest) -> JsonResponse:
    posts = (
        Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=timezone.now())
        .select_related("author")
        .order_by("-published_at")[:5]
    )
    items = [
        {
            "title": p.title,
            "slug": p.slug,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]
    return JsonResponse({"items": items})


def widget_bounty_posts(request: HttpRequest) -> JsonResponse:
    posts = (
        Post.objects.filter(
            status=PostStatus.PUBLISHED,
            publish_at__lte=timezone.now(),
            tags__slug="bounty",
        )
        .select_related("author")
        .distinct()
        .order_by("-published_at")[:5]
    )
    items = [
        {
            "title": p.title,
            "slug": p.slug,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in posts
    ]
    return JsonResponse({"items": items})
