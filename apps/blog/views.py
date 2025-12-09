
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.views.decorators.cache import cache_page
from django.template.loader import render_to_string
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

import hashlib
import logging

from apps.core.views import _get_site_settings_snapshot
from apps.core.app_service import AppService
from .forms import PostForm
from .models import Post, PostStatus, Category, PostDraft, PostRevision
from apps.tags.models import Tag
from apps.tags import services as tag_services
from apps.seo.models import SEOModel, Metadata
from apps.core.utils import feature_flags
from apps.users.models import CustomUser
from apps.core import ai
from apps.core import ai_client
from apps.blog.services import ai_editor, workflow
from apps.core.utils.logging import log_event
from apps.i18n.services import resolve_locale
from apps.blog.models import PostTranslation, CategoryTranslation, TagTranslation

logger = logging.getLogger(__name__)

def _sync_tag_usage(tags_qs):
    for tag in tags_qs:
        try:
            count = tag.posts.filter(
                status=PostStatus.PUBLISHED, publish_at__lte=timezone.now()
            ).count()
            if tag.usage_count != count:
                tag.usage_count = count
                tag.save(update_fields=["usage_count"])
        except Exception:
            continue


def _apply_translations_to_posts(posts, locale: str | None):
    """
    Apply translations to a list/queryset of posts for the given locale.
    Mutates objects in place for display purposes.
    """
    if not locale:
        return posts
    post_ids = [p.id for p in posts if getattr(p, "id", None)]
    if not post_ids:
        return posts
    translations = {
        pt.post_id: pt
        for pt in PostTranslation.objects.filter(post_id__in=post_ids, language=locale)
    }
    categories = {p.category_id for p in posts if getattr(p, "category_id", None)}
    cat_translations = {
        ct.category_id: ct
        for ct in CategoryTranslation.objects.filter(category_id__in=categories, language=locale)
    } if categories else {}

    tag_ids = set()
    for p in posts:
        try:
            for t in p.tags.all():
                tag_ids.add(t.id)
        except Exception:
            continue
    tag_translations = {
        tt.tag_id: tt
        for tt in TagTranslation.objects.filter(tag_id__in=tag_ids, language=locale)
    } if tag_ids else {}

    for p in posts:
        pt = translations.get(p.id)
        if pt:
            p.title = pt.title or p.title
            p.summary = pt.summary or p.summary
            p.body = pt.body or p.body
            p.seo_title = pt.seo_title or p.seo_title
            p.seo_description = pt.seo_description or p.seo_description
        if p.category_id and p.category_id in cat_translations:
            try:
                p.category.name = cat_translations[p.category_id].name or p.category.name
            except Exception:
                pass
        try:
            for t in p.tags.all():
                tt = tag_translations.get(t.id)
                if tt:
                    t.name = tt.name or t.name
        except Exception:
            pass
    return posts


def _ensure_post_seo(post: Post, request: HttpRequest | None = None):
    """
    Ensure SEO metadata/linkable entry for a post when SEO is enabled.
    """
    try:
        seo_api = AppService.get("seo")
        seo_settings = seo_api.get_settings() if seo_api and hasattr(seo_api, "get_settings") else {}
        if not seo_settings.get("seo_enabled", True):
            return
    except Exception:
        if not feature_flags.seo_enabled():
            return
    try:
        ct = ContentType.objects.get_for_model(Post)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=post.pk)
        if seo_obj.locked:
            return

        meta, _ = Metadata.objects.get_or_create(seo=seo_obj)
        settings_snapshot = _get_site_settings_snapshot()
        try:
            seo_api = AppService.get("seo")
            seo_settings = seo_api.get_settings() if seo_api and hasattr(seo_api, "get_settings") else {}
        except Exception:
            seo_settings = {}
        auto_meta = seo_settings.get("auto_meta_enabled", settings_snapshot.get("auto_meta_enabled", False))

        content_hash = hashlib.sha256(
            f"{post.title}|{post.summary}|{post.body}".encode("utf-8")
        ).hexdigest()
        has_changes = meta.content_hash != content_hash

        if auto_meta or not meta.meta_title:
            meta.meta_title = (post.seo_title or post.title)[:255]
        if auto_meta or not meta.meta_description:
            meta.meta_description = (post.seo_description or post.summary[:320])[:320]
        if not meta.canonical_url and request:
            meta.canonical_url = request.build_absolute_uri()
        if hasattr(post, "noindex"):
            meta.noindex = bool(post.noindex)

        if has_changes and auto_meta:
            meta.content_hash = content_hash
            meta.generated_at = timezone.now()

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
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_api = None
        blog_settings = {}

    blog_enabled = blog_settings.get("enable_blog", False if blog_api is None else settings_snapshot.get("enable_blog", True))
    if not blog_enabled and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Blog is disabled.")
    allow_user_posts = blog_settings.get("allow_user_blog_posts", settings_snapshot.get("allow_user_blog_posts", False))

    now_ts = timezone.now()
    base_qs = Post.objects.select_related("author", "category").prefetch_related("tags")
    published_qs = base_qs.filter(status=PostStatus.PUBLISHED, publish_at__lte=now_ts)

    # If owner/staff, also show their drafts/scheduled in manager context (not to the public)
    show_unpublished = request.user.is_authenticated and (request.user.is_staff or allow_user_posts)
    if show_unpublished:
        own_unpublished = base_qs.filter(author=request.user, status__in=[PostStatus.DRAFT, PostStatus.SCHEDULED])
        posts = (published_qs | own_unpublished).distinct()
    else:
        posts = published_qs
    q = request.GET.get("q", "").strip()
    tag = request.GET.get("tag", "").strip()
    category_slug = request.GET.get("category", "").strip()
    author = request.GET.get("author", "").strip()
    status_filter = (request.GET.get("status") or "").strip().lower()
    sort = (request.GET.get("sort") or "recent").strip().lower()
    date_from = request.GET.get("from") or ""
    date_to = request.GET.get("to") or ""

    if q:
        vector = (
            SearchVector("title", weight="A")
            + SearchVector("summary", weight="B")
            + SearchVector("body", weight="C")
            + SearchVector("tags__name", weight="B")
            + SearchVector("category__name", weight="C")
        )
        query = SearchQuery(q, search_type="plain")
        posts = (
            posts.annotate(rank=SearchRank(vector, query))
            .filter(rank__gte=0.05)
            .order_by("-rank", "-published_at")
        )
    if tag:
        posts = posts.filter(Q(tags__slug=tag) | Q(tags__name__iexact=tag))
    if category_slug:
        posts = posts.filter(Q(category__slug=category_slug) | Q(category__parent__slug=category_slug))
    if author:
        posts = posts.filter(author__username=author)
    if date_from:
        try:
            df = timezone.datetime.fromisoformat(date_from)
            posts = posts.filter(publish_at__gte=df)
        except Exception:
            pass
    if date_to:
        try:
            dt = timezone.datetime.fromisoformat(date_to)
            posts = posts.filter(publish_at__lte=dt)
        except Exception:
            pass

    # Sorting
    if sort == "featured":
        posts = posts.order_by("-featured", "-published_at")
    elif sort == "oldest":
        posts = posts.order_by("published_at")
    elif sort == "title":
        posts = posts.order_by("title")
    else:
        sort = "recent"
        posts = posts.order_by("-published_at")

    posts = posts.prefetch_related("tags").distinct()

    # Status filter (only staff/author can view non-published states)
    if status_filter in PostStatus.values:
        if status_filter == PostStatus.PUBLISHED:
            posts = posts.filter(status=PostStatus.PUBLISHED, publish_at__lte=now_ts)
        elif request.user.is_staff or request.user.is_superuser:
            posts = posts.filter(status=status_filter)
        elif request.user.is_authenticated:
            posts = posts.filter(status=status_filter, author=request.user)
        # else: ignore invalid visibility requests
    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    current_locale = resolve_locale(request, "blog")
    _apply_translations_to_posts(page_obj.object_list, current_locale)
    # Precompute display strings to keep templates simple and avoid filter gymnastics.
    for p in page_obj:
        published = p.published_at.strftime("%b %d, %Y") if p.published_at else "Draft"
        p.meta_text = f"By {p.author} · {published}"

    trending_tags = Tag.objects.order_by("-usage_count")[:10]
    for t in trending_tags:
        t.live_post_count = t.posts.filter(
            status=PostStatus.PUBLISHED, publish_at__lte=now_ts
        ).count()

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
    context = {
        "posts": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "trending_tags": trending_tags,
        "trending_posts": trending_posts,
        "latest_posts": latest_posts,
        "allow_user_posts": allow_user_posts,
        "active_status": status_filter,
        "active_tag": tag,
        "active_category": category_slug,
        "active_author": author,
        "date_from": date_from,
        "date_to": date_to,
        "categories": Category.objects.select_related("parent").order_by("parent__name", "name"),
        "status_filters": [
            ("", "All"),
            (PostStatus.PUBLISHED, "Published"),
            (PostStatus.SCHEDULED, "Scheduled"),
            (PostStatus.DRAFT, "Drafts"),
        ],
        "sort": sort,
        "sort_options": [
            ("recent", "Newest"),
            ("featured", "Featured first"),
            ("oldest", "Oldest"),
            ("title", "Title A-Z"),
        ],
    }
    return render(request, "blog/post_list.html", context)


def post_detail(request: HttpRequest, slug: str) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_api = None
        blog_settings = {}
    blog_enabled = blog_settings.get("enable_blog", False if blog_api is None else settings_snapshot.get("enable_blog", True))
    if not blog_enabled and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Blog is disabled.")
    allow_user_posts = blog_settings.get("allow_user_blog_posts", settings_snapshot.get("allow_user_blog_posts", False))

    base_qs = Post.objects.select_related("author", "category").prefetch_related("tags")
    post = get_object_or_404(base_qs, slug__iexact=slug)
    # Non-staff users must only see live posts
    if not (request.user.is_staff or request.user == post.author):
        if not post.is_live:
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
    _ensure_post_seo(post, request)

    # Tag cloud weights for sidebar (simple 3-tier scaling)
    tag_cloud_raw = list(Tag.objects.filter(is_active=True).order_by("-usage_count")[:30])
    if tag_cloud_raw:
        max_usage = max([t.usage_count or 1 for t in tag_cloud_raw]) or 1
        for t in tag_cloud_raw:
            ratio = (t.usage_count or 0) / max_usage
            if ratio >= 0.66:
                t.weight = "lg"
            elif ratio >= 0.33:
                t.weight = "md"
            else:
                t.weight = "sm"
    else:
        tag_cloud_raw = []

    canonical = post.canonical_url or request.build_absolute_uri()
    current_locale = resolve_locale(request, "blog")

    # Apply translations when available
    if current_locale:
        _apply_translations_to_posts(trending_posts, current_locale)
        try:
            t = PostTranslation.objects.filter(post=post, language=current_locale).first()
            if t:
                post.title = t.title or post.title
                post.summary = t.summary or post.summary
                post.body = t.body or post.body
                post.seo_title = t.seo_title or post.seo_title
                post.seo_description = t.seo_description or post.seo_description
        except Exception:
            pass
        try:
            if post.category:
                ct = CategoryTranslation.objects.filter(category=post.category, language=current_locale).first()
                if ct:
                    post.category.name = ct.name or post.category.name
        except Exception:
            pass
        # tags
        try:
            translated_tags = {}
            for tag in post.tags.all():
                tt = TagTranslation.objects.filter(tag=tag, language=current_locale).first()
                if tt:
                    translated_tags[tag.id] = tt.name
            if translated_tags:
                for tag in post.tags.all():
                    if tag.id in translated_tags:
                        tag.name = translated_tags[tag.id]
        except Exception:
            pass

    return render(
        request,
        "blog/post_detail.html",
        {
            "post": post,
            "related_widget_html": related_widget_html,
            "trending_tags": trending_tags,
            "trending_posts": trending_posts,
            "allow_user_posts": allow_user_posts,
            "tag_cloud": tag_cloud_raw,
            "canonical_url": canonical,
            "current_locale": current_locale,
        },
    )


@require_GET
def post_archive_year(request: HttpRequest, year: int) -> HttpResponse:
    posts = Post.objects.filter(
        status=PostStatus.PUBLISHED,
        publish_at__year=year,
        publish_at__lte=timezone.now(),
    ).select_related("author", "category")
    current_locale = resolve_locale(request, "blog")
    _apply_translations_to_posts(posts, current_locale)
    return render(
        request,
        "blog/archive_year.html",
        {"posts": posts, "year": year, "current_locale": current_locale},
    )


@require_GET
def post_archive_month(request: HttpRequest, year: int, month: int) -> HttpResponse:
    posts = Post.objects.filter(
        status=PostStatus.PUBLISHED,
        publish_at__year=year,
        publish_at__month=month,
        publish_at__lte=timezone.now(),
    ).select_related("author", "category")
    current_locale = resolve_locale(request, "blog")
    _apply_translations_to_posts(posts, current_locale)
    return render(
        request,
        "blog/archive_month.html",
        {"posts": posts, "year": year, "month": month, "current_locale": current_locale},
    )


@require_GET
def posts_api_public(request: HttpRequest) -> JsonResponse:
    """
    Lightweight public posts API (read-only).
    """
    qs = (
        Post.objects.filter(status=PostStatus.PUBLISHED, publish_at__lte=timezone.now())
        .select_related("author", "category")
        .prefetch_related("tags")
        .order_by("-published_at")[:50]
    )
    current_locale = resolve_locale(request, "blog")
    _apply_translations_to_posts(qs, current_locale)
    data = []
    for p in qs:
        data.append(
            {
                "title": p.title,
                "slug": p.slug,
                "summary": p.summary,
                "url": request.build_absolute_uri(p.get_absolute_url()),
                "category": p.category.name if p.category else None,
                "tags": [t.name for t in p.tags.all()],
                "published_at": p.published_at.isoformat() if p.published_at else None,
            }
        )
    return JsonResponse({"items": data})


@login_required
def manage_posts(request: HttpRequest) -> HttpResponse:
    """
    Simple manager view for drafts and scheduled posts.
    Staff sees all; authors see their own.
    """
    settings_snapshot = _get_site_settings_snapshot()
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_settings = {}
    allow_user_posts = blog_settings.get("allow_user_blog_posts", settings_snapshot.get("allow_user_blog_posts", False))
    if not (request.user.is_staff or request.user.is_superuser or allow_user_posts):
        raise Http404()

    base_qs = Post.objects.select_related("author", "category")
    if request.user.is_staff or request.user.is_superuser:
        drafts = base_qs.filter(status=PostStatus.DRAFT).order_by("-updated_at", "-created_at")[:50]
        scheduled = base_qs.filter(status=PostStatus.SCHEDULED).order_by("publish_at")[:50]
    else:
        drafts = base_qs.filter(author=request.user, status=PostStatus.DRAFT).order_by("-updated_at", "-created_at")[:50]
        scheduled = base_qs.filter(author=request.user, status=PostStatus.SCHEDULED).order_by("publish_at")[:50]

    return render(
        request,
        "blog/manage.html",
        {
            "drafts": drafts,
            "scheduled": scheduled,
            "allow_user_posts": allow_user_posts,
        },
    )


@login_required
@require_POST
def bulk_publish(request: HttpRequest) -> HttpResponse:
    """
    Bulk publish selected posts (staff or owners).
    """
    ids = request.POST.getlist("post_id")
    if not ids:
        messages.info(request, "No posts selected.")
        return redirect("blog:manage_posts")
    qs = Post.objects.filter(pk__in=ids, status__in=[PostStatus.DRAFT, PostStatus.SCHEDULED])
    if not (request.user.is_staff or request.user.is_superuser):
        qs = qs.filter(author=request.user)
    updated = 0
    with transaction.atomic():
        for post in qs:
            post.status = PostStatus.PUBLISHED
            post.publish_at = timezone.now()
            post.published_at = timezone.now()
            post.save(update_fields=["status", "publish_at", "published_at", "updated_at"])
            updated += 1
    try:
        log_event(
            logger,
            "info",
            "blog.bulk_publish",
            actor=request.user.pk,
            count=updated,
            ids=",".join(ids),
        )
    except Exception:
        logger.debug("bulk_publish audit log failed", exc_info=True)
    messages.success(request, f"Published {updated} posts.")
    return redirect("blog:manage_posts")


@login_required
@require_http_methods(["GET", "POST"])
def post_create(request: HttpRequest) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()
    try:
        blog_api = AppService.get("blog")
        blog_settings = blog_api.get_settings() if blog_api and hasattr(blog_api, "get_settings") else {}
    except Exception:
        blog_api = None
        blog_settings = {}
    blog_enabled = blog_settings.get("enable_blog", False if blog_api is None else settings_snapshot.get("enable_blog", True))
    if not blog_enabled and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Blog is disabled.")

    allow_user_posts = blog_settings.get("allow_user_blog_posts", settings_snapshot.get("allow_user_blog_posts", False))
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

    edit_slug = request.GET.get("edit") or request.POST.get("edit")
    instance = None
    if edit_slug:
        instance = get_object_or_404(Post, slug__iexact=edit_slug)
        if not (request.user.is_staff or request.user.is_superuser or instance.author == request.user):
            raise Http404()

    if request.method == "POST":
        form = PostForm(request.POST, instance=instance)
        if form.is_valid():
            post = form.save(commit=False)
            if not instance:
                post.author = request.user
            with transaction.atomic():
                post.save()
                form.save_m2m()
                # If no tags supplied, auto-suggest from content
                if not post.tags.exists():
                    tag_services.auto_tag_post(post, allow_create=True, max_tags=5)
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
            messages.success(request, "Post updated." if instance else "Post saved.")
            return redirect("blog:post_detail", slug=post.slug)
    else:
        form = PostForm(instance=instance)
    return render(request, "blog/post_form.html", {"form": form, "editing": bool(instance), "editing_post": instance})


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


@login_required
@require_POST
def api_ai_assist(request: HttpRequest) -> JsonResponse:
    """
    AI assist endpoint for the blog editor.
    Actions: generate_title, summarize, improve, translate (stub), suggest_seo.
    """
    action = request.POST.get("action") or ""
    text = request.POST.get("text") or ""
    context = request.POST.get("context") or ""
    if not action:
        return JsonResponse({"ok": False, "error": "missing_action"}, status=400)

    # Respect feature flags
    if not feature_flags.seo_enabled() and action in {"suggest_seo"}:
        return JsonResponse({"ok": False, "error": "seo_disabled"}, status=403)

    try:
        if action == "generate_title":
            suggestion = ai_client.generate_title(text, request.user)
            return JsonResponse({"ok": True, "suggestion": suggestion[:240]})
        if action == "summarize":
            summary = ai_client.summarize_text(text or context, request.user)
            return JsonResponse({"ok": True, "suggestion": summary})
        if action == "improve":
            improved = ai_editor.rewrite_paragraph(text or context, tone="concise")
            return JsonResponse({"ok": True, "suggestion": improved})
        if action == "suggest_seo":
            desc = ai_client.generate_seo_description(text or context, request.user)
            return JsonResponse({"ok": True, "suggestion": desc})
        if action == "outline":
            outline = ai_editor.suggest_outline(text or context)
            return JsonResponse({"ok": True, "suggestion": outline})
        if action == "suggest_tags":
            tags_payload = ai_editor.suggest_tags(text or context)
            return JsonResponse({"ok": True, **tags_payload})
        return JsonResponse({"ok": False, "error": "unknown_action"}, status=400)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)


@login_required
@require_POST
def api_workflow(request: HttpRequest, slug: str) -> JsonResponse:
    """
    Workflow transitions for posts (request_review, schedule, publish, archive).
    """
    action = request.POST.get("action")
    when = request.POST.get("when")
    post = get_object_or_404(Post, slug=slug)
    if not action:
        return JsonResponse({"ok": False, "error": "missing_action"}, status=400)
    if action not in {"request_review", "schedule", "publish", "archive"}:
        return JsonResponse({"ok": False, "error": "invalid_action"}, status=400)
    try:
        if action == "request_review":
            res = workflow.request_review(post, user=request.user)
        elif action == "schedule":
            when_dt = timezone.datetime.fromisoformat(when) if when else timezone.now()
            res = workflow.schedule(post, when=when_dt, user=request.user)
        elif action == "publish":
            res = workflow.publish(post, user=request.user)
        else:
            res = workflow.archive(post, user=request.user)
        log_event(
            logger,
            "info",
            "blog.workflow.transition",
            action=action,
            post=post.slug,
            user=request.user.pk,
            status=res.status,
            correlation_id=getattr(request, "correlation_id", None),
        )
        return JsonResponse({"ok": res.ok, "status": res.status, "message": res.message})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)


@require_GET
def api_similar_posts(request: HttpRequest) -> JsonResponse:
    """
    Suggest existing posts similar to a title/summary for collision checks and inspiration.
    """
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"items": []})
    posts = (
        Post.objects.filter(Q(title__icontains=q) | Q(summary__icontains=q))
        .select_related("author")
        .order_by("-published_at")[:8]
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


