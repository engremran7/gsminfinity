from __future__ import annotations

from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect

from apps.pages.models import Page

from .views_shared import _ADMIN_DISABLED, _make_breadcrumb, _render_admin


# Extracted views_content views from legacy views.py
class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = [
            "title",
            "slug",
            "status",
            "access_level",
            "include_in_sitemap",
            "changefreq",
            "priority",
            "content_format",
            "content",
            "publish_at",
            "unpublish_at",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "unpublish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = (
            "border border-slate-300 rounded px-2 py-1 w-full bg-white text-slate-900"
        )
        for name, field in self.fields.items():
            if name in {"include_in_sitemap"}:
                continue
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{classes} {base_class}".strip()


@csrf_protect
@staff_member_required
def admin_suite_pages(request: HttpRequest) -> HttpResponse:
    """Full-featured pages management inside Admin Suite."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    edit_page = None

    if request.method == "POST":
        action = request.POST.get("action") or ""
        page_id = request.POST.get("page_id")
        if action in {"publish", "unpublish", "delete"} and page_id:
            page = Page.objects.filter(pk=page_id).first()
            if page:
                if action == "delete":
                    page.delete()
                    message = f"Deleted page {page.slug}."
                elif action == "publish":
                    page.status = "published"
                    page.save(update_fields=["status", "updated_at"])
                    message = f"Published {page.slug}."
                elif action == "unpublish":
                    page.status = "draft"
                    page.save(update_fields=["status", "updated_at"])
                    message = f"Unpublished {page.slug}."
        elif action == "save":
            instance = Page.objects.filter(pk=page_id).first() if page_id else None
            form = PageForm(request.POST, instance=instance)
            if form.is_valid():
                page = form.save(commit=False)
                if instance is None:
                    page.created_by = request.user
                page.updated_by = request.user
                page.save()
                message = f"Saved page {page.slug}."
            else:
                edit_page = instance
                message = "Please correct the errors below."

    if request.method == "GET" and request.GET.get("page_id"):
        edit_page = Page.objects.filter(pk=request.GET.get("page_id")).first()

    form = PageForm(instance=edit_page)

    pages = list(Page.objects.order_by("-updated_at")[:200])
    stats = {
        "total": Page.objects.count(),
        "published": Page.objects.filter(status="published").count(),
        "drafts": Page.objects.filter(status="draft").count(),
        "archived": Page.objects.filter(status="archived").count(),
        "sitemap": Page.objects.filter(
            include_in_sitemap=True, status="published"
        ).count(),
    }

    return _render_admin(
        request,
        "admin_suite/pages.html",
        {
            "pages": pages,
            "form": form,
            "edit_page": edit_page,
            "stats": stats,
            "message": message,
        },
        nav_active="pages",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Pages", None)
        ),
        subtitle="Pages (public) management",
    )


@staff_member_required
def admin_suite_blog(request: HttpRequest) -> HttpResponse:
    """
    Blog management (create/edit/publish) inside Admin Suite to replace legacy Django admin usage.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    try:
        from apps.blog.models import Category, Post, PostStatus
    except Exception:
        raise Http404("Blog module not installed")

    class BlogPostForm(forms.ModelForm):
        class Meta:
            model = Post
            fields = [
                "title",
                "slug",
                "status",
                "publish_at",
                "seo_title",
                "seo_description",
                "canonical_url",
                "summary",
                "body",
                "category",
                "featured",
            ]
            widgets = {
                "publish_at": forms.DateTimeInput(
                    attrs={
                        "type": "datetime-local",
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900",
                    }
                ),
                "summary": forms.Textarea(
                    attrs={
                        "rows": 2,
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900",
                    }
                ),
                "body": forms.Textarea(
                    attrs={
                        "rows": 8,
                        "class": "w-full border rounded px-2 py-2 bg-white text-slate-900",
                    }
                ),
                "title": forms.TextInput(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "slug": forms.TextInput(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "seo_title": forms.TextInput(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "seo_description": forms.Textarea(
                    attrs={
                        "rows": 2,
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900",
                    }
                ),
                "canonical_url": forms.URLInput(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "status": forms.Select(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "category": forms.Select(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "featured": forms.CheckboxInput(
                    attrs={"class": "h-4 w-4 text-primary"}
                ),
            }

    message = ""
    edit_post = None

    if request.method == "POST":
        action = request.POST.get("action")
        post_id = request.POST.get("post_id")
        if action in {"delete", "publish", "unpublish"} and post_id:
            try:
                target = Post.objects.get(pk=post_id)
                if action == "delete":
                    target.delete()
                    message = "Post deleted."
                elif action == "publish":
                    target.status = PostStatus.PUBLISHED
                    target.save()
                    message = "Post published."
                elif action == "unpublish":
                    target.status = PostStatus.DRAFT
                    target.save()
                    message = "Post moved to draft."
            except Exception as exc:
                message = f"Action failed: {exc}"
        elif action == "save":
            instance = Post.objects.filter(pk=post_id).first() if post_id else None
            form = BlogPostForm(request.POST, instance=instance)
            if form.is_valid():
                post = form.save(commit=False)
                if not post.author_id:
                    post.author = getattr(request, "user", None)
                post.save()
                form.save_m2m()
                message = "Post saved."
                edit_post = post
            else:
                edit_post = instance
        return redirect(f"{reverse('admin_suite:admin_suite_blog')}?message={message}")

    if request.method == "GET" and request.GET.get("post_id"):
        edit_post = Post.objects.filter(pk=request.GET.get("post_id")).first()
    form = BlogPostForm(instance=edit_post)
    if request.GET.get("message"):
        message = request.GET.get("message")

    posts = list(Post.objects.order_by("-updated_at")[:200])
    stats = {
        "total": Post.objects.count(),
        "published": Post.objects.filter(status=PostStatus.PUBLISHED).count(),
        "drafts": Post.objects.filter(status=PostStatus.DRAFT).count(),
        "scheduled": Post.objects.filter(status=PostStatus.SCHEDULED).count(),
        "archived": Post.objects.filter(status=PostStatus.ARCHIVED).count(),
    }

    # SEO helper: suggested tags and health capsule for the edit target
    suggested_tags = []
    seo_health = {}
    if edit_post:
        try:
            from apps.seo.auto import ensure_canonical, suggest_tags

            suggested_tags = suggest_tags(
                [edit_post.title, edit_post.summary or "", edit_post.body], max_tags=6
            )
            seo_health = {
                "title_len": len(edit_post.title or ""),
                "desc_len": len(edit_post.seo_description or edit_post.summary or ""),
                "word_count": len((edit_post.body or "").split()),
                "tag_count": edit_post.tags.count(),
                "canonical": ensure_canonical(edit_post) or "",
            }
        except Exception:
            suggested_tags = []
            seo_health = {}

    return _render_admin(
        request,
        "admin_suite/blog.html",
        {
            "posts": posts,
            "form": form,
            "edit_post": edit_post,
            "message": message,
            "categories": Category.objects.all()[:100],
            "stats": stats,
            "suggested_tags": suggested_tags,
            "seo_health": seo_health,
        },
        nav_active="blog",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Blog", None)
        ),
        subtitle="Blog posts management",
    )


@csrf_protect
@staff_member_required
def admin_suite_blog_categories(request: HttpRequest) -> HttpResponse:
    """
    Blog category management inside Admin Suite.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    try:
        from apps.blog.models import Category
    except Exception:
        raise Http404("Blog module not installed")

    class CategoryForm(forms.ModelForm):
        class Meta:
            model = Category
            fields = ["name", "slug", "parent"]
            widgets = {
                "name": forms.TextInput(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "slug": forms.TextInput(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
                "parent": forms.Select(
                    attrs={
                        "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"
                    }
                ),
            }

    message = ""
    edit_category = None

    if request.method == "POST":
        action = request.POST.get("action")
        category_id = request.POST.get("category_id")

        if action == "delete" and category_id:
            try:
                Category.objects.get(pk=category_id).delete()
                message = "Category deleted."
            except Exception as exc:
                message = f"Delete failed: {exc}"
        elif action == "save":
            instance = (
                Category.objects.filter(pk=category_id).first() if category_id else None
            )
            form = CategoryForm(request.POST, instance=instance)
            if form.is_valid():
                form.save()
                message = "Category saved."
            else:
                edit_category = instance
                message = "Please correct errors."

    if request.method == "GET" and request.GET.get("category_id"):
        edit_category = Category.objects.filter(
            pk=request.GET.get("category_id")
        ).first()

    form = CategoryForm(instance=edit_category)
    categories = list(Category.objects.order_by("name"))

    return _render_admin(
        request,
        "admin_suite/blog_categories.html",
        {
            "categories": categories,
            "form": form,
            "edit_category": edit_category,
            "message": message,
        },
        nav_active="blog",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Blog", "admin_suite:admin_suite_blog"),
            ("Categories", None),
        ),
        subtitle="Blog categories",
    )


@staff_member_required
def admin_suite_content(request: HttpRequest) -> HttpResponse:
    """Content/SEO overview (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "posts_total": 0,
        "posts_published": 0,
        "posts_draft": 0,
        "comments_pending": 0,
        "comments_spam": 0,
    }
    posts: list[Dict[str, Any]] = []
    comments: list[Dict[str, Any]] = []

    try:
        from apps.blog.models import Post, PostStatus

        stats["posts_total"] = Post.objects.count()
        stats["posts_published"] = Post.objects.filter(
            status=PostStatus.PUBLISHED
        ).count()
        stats["posts_draft"] = Post.objects.filter(status=PostStatus.DRAFT).count()
        posts = list(
            Post.objects.filter(status=PostStatus.PUBLISHED)
            .order_by("-published_at")[:10]
            .values("title", "slug", "published_at", "author_id")
        )
    except Exception as exc:
        logger.debug("Admin suite content posts snapshot failed: %s", exc)

    try:
        from apps.comments.models import Comment

        stats["comments_pending"] = Comment.objects.filter(
            status=Comment.Status.PENDING
        ).count()
        stats["comments_spam"] = Comment.objects.filter(
            status=Comment.Status.SPAM
        ).count()
        comments = list(
            Comment.objects.filter(status=Comment.Status.PENDING)
            .order_by("-created_at")[:10]
            .values("id", "user_id", "body", "created_at", "post_id")
        )
    except Exception as exc:
        logger.debug("Admin suite content comments snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/content.html",
        {
            "stats": stats,
            "posts": posts,
            "comments": comments,
        },
        nav_active="content",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Content", None)
        ),
        subtitle="Posts, comments, and moderation status",
    )


@staff_member_required
def admin_suite_marketing(request: HttpRequest) -> HttpResponse:
    """Ads + SEO overview (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "placements": 0,
        "creatives": 0,
        "impressions_24h": 0,
        "clicks_24h": 0,
        "redirects": 0,
        "sitemap_urls": 0,
    }
    placements: list[Dict[str, Any]] = []
    redirects: list[Dict[str, Any]] = []

    # Ads snapshot
    try:
        from django.utils import timezone

        from apps.ads.models import AdCreative, AdEvent, AdPlacement

        stats["placements"] = AdPlacement.objects.count()
        stats["creatives"] = AdCreative.objects.count()
        since = timezone.now() - timezone.timedelta(hours=24)
        stats["impressions_24h"] = AdEvent.objects.filter(
            event_type="impression", created_at__gte=since
        ).count()
        stats["clicks_24h"] = AdEvent.objects.filter(
            event_type="click", created_at__gte=since
        ).count()
        placements = list(
            AdPlacement.objects.order_by("-updated_at")[:10].values(
                "name", "slug", "page_context", "updated_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite ads snapshot failed: %s", exc)

    # SEO snapshot
    try:
        from apps.seo.models import Redirect, SitemapEntry

        stats["redirects"] = Redirect.objects.count()
        stats["sitemap_urls"] = SitemapEntry.objects.count()
        redirects = list(
            Redirect.objects.order_by("-updated_at")[:10].values(
                "source", "target", "is_permanent", "updated_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite seo snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/marketing.html",
        {
            "stats": stats,
            "placements": placements,
            "redirects": redirects,
        },
        nav_active="marketing",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Marketing", None)
        ),
        subtitle="Ads and SEO snapshots",
    )


@staff_member_required
@csrf_protect
def admin_suite_ai(request: HttpRequest) -> HttpResponse:
    """AI settings snapshot and basic health check."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    sample_output = None
    ai_status: Dict[str, Any] = {}

    try:
        cfg = AISettings.get_solo()
        ai_status = {
            "provider": getattr(cfg, "provider", ""),
            "model": getattr(cfg, "model", ""),
            "mock_mode": bool(getattr(cfg, "mock_mode", False)),
            "enabled": bool(getattr(cfg, "enabled", True)),
        }
    except Exception as exc:
        logger.debug("Admin suite AI settings unavailable: %s", exc)
        message = "AI settings unavailable."

    if request.method == "POST" and request.POST.get("action") == "test":
        try:
            sample_output = test_completion()
            message = "Test completion succeeded."
        except AIProviderError as exc:
            message = f"Provider error: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            message = f"Test failed: {exc}"

    return _render_admin(
        request,
        "admin_suite/ai.html",
        {
            "ai_status": ai_status,
            "sample_output": sample_output,
            "message": message,
        },
        nav_active="ai",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("AI", None)
        ),
        subtitle="AI settings and health checks",
    )


@staff_member_required
def admin_suite_distribution(request: HttpRequest) -> HttpResponse:
    """Distribution overview."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "accounts": 0,
        "plans": 0,
        "jobs_pending": 0,
        "jobs_failed": 0,
        "logs_24h": 0,
    }
    accounts: list[Dict[str, Any]] = []
    plans: list[Dict[str, Any]] = []
    jobs: list[Dict[str, Any]] = []
    logs: list[Dict[str, Any]] = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 10
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(50, int(request.GET.get("page_size", "10"))))
    except Exception:
        page = 1
        page_size = 10
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.distribution.models import ShareJob, SharePlan, SocialAccount

            if action == "disable_account":
                aid = request.POST.get("account_id")
                SocialAccount.objects.filter(pk=aid).update(is_active=False)
                message = "Account disabled."
            elif action == "enable_account":
                aid = request.POST.get("account_id")
                SocialAccount.objects.filter(pk=aid).update(is_active=True)
                message = "Account enabled."
            elif action == "save_account":
                aid = request.POST.get("account_id")
                fields = {
                    "channel": (request.POST.get("channel") or "")[:50],
                    "account_name": (request.POST.get("account_name") or "")[:255],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if aid:
                    SocialAccount.objects.filter(pk=aid).update(**fields)
                else:
                    SocialAccount.objects.create(**fields)
                message = "Account saved."
            elif action == "save_plan":
                pid = request.POST.get("plan_id")
                fields = {
                    "name": (request.POST.get("name") or "")[:255],
                    "description": (request.POST.get("description") or "")[:500],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if pid:
                    SharePlan.objects.filter(pk=pid).update(**fields)
                else:
                    SharePlan.objects.create(**fields)
                message = "Plan saved."
            elif action == "retry_job":
                jid = request.POST.get("job_id")
                ShareJob.objects.filter(pk=jid).update(status="pending", last_error="")
                message = "Job retried."
            elif action == "delete_job":
                jid = request.POST.get("job_id")
                ShareJob.objects.filter(pk=jid).delete()
                message = "Job deleted."
        except Exception as exc:
            logger.warning("Admin suite distribution toggle failed: %s", exc)
            message = "Action failed."

    try:
        from django.utils import timezone

        from apps.distribution.models import (
            ShareJob,
            ShareLog,
            SharePlan,
            SocialAccount,
        )

        stats["accounts"] = SocialAccount.objects.count()
        stats["plans"] = SharePlan.objects.count()
        stats["jobs_pending"] = ShareJob.objects.filter(status="pending").count()
        stats["jobs_failed"] = ShareJob.objects.filter(status="failed").count()

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["logs_24h"] = ShareLog.objects.filter(created_at__gte=since).count()

        account_qs = SocialAccount.objects.order_by("channel", "account_name")
        plan_qs = SharePlan.objects.order_by("-created_at")
        if query:
            from django.db.models import Q

            account_qs = account_qs.filter(
                Q(channel__icontains=query) | Q(account_name__icontains=query)
            )
            plan_qs = plan_qs.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
            jobs_qs = ShareJob.objects.order_by("-created_at").filter(
                Q(channel__icontains=query) | Q(status__icontains=query)
            )
            logs_qs = ShareLog.objects.order_by("-created_at").filter(
                Q(level__icontains=query) | Q(message__icontains=query)
            )
        else:
            jobs_qs = ShareJob.objects.order_by("-created_at")
            logs_qs = ShareLog.objects.order_by("-created_at")

        accounts = list(
            account_qs[:20].values(
                "id", "channel", "account_name", "is_active", "token_expires_at"
            )
        )
        plans = list(
            plan_qs[:20].values("id", "name", "description", "is_active", "created_at")
        )
        jobs = list(
            jobs_qs[offset : offset + page_size].values(
                "id", "channel", "status", "created_at", "attempt_count", "last_error"
            )
        )
        logs = list(
            logs_qs[offset : offset + page_size].values(
                "job_id", "level", "message", "created_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite distribution snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/distribution.html",
        {
            "stats": stats,
            "accounts": accounts,
            "plans": plans,
            "jobs": jobs,
            "logs": logs,
            "message": message,
            "q": query,
            "page": page,
            "page_size": page_size,
        },
        nav_active="distribution",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Distribution", None)
        ),
        subtitle="Accounts, plans, jobs, and logs",
    )


@staff_member_required
def admin_suite_ads(request: HttpRequest) -> HttpResponse:
    """Ads read-only dashboard: placements, creatives, events stats."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "placements": 0,
        "creatives": 0,
        "impressions_24h": 0,
        "clicks_24h": 0,
    }
    placements: list[Dict[str, Any]] = []
    creatives: list[Dict[str, Any]] = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 20
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(50, int(request.GET.get("page_size", "20"))))
    except Exception:
        page = 1
        page_size = 20
    offset = (page - 1) * page_size
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ads.models import AdCreative, AdPlacement

            if action == "disable_placement":
                pid = request.POST.get("placement_id")
                AdPlacement.objects.filter(pk=pid).update(is_active=False)
            elif action == "enable_placement":
                pid = request.POST.get("placement_id")
                AdPlacement.objects.filter(pk=pid).update(is_active=True)
            elif action == "disable_creative":
                cid = request.POST.get("creative_id")
                AdCreative.objects.filter(pk=cid).update(is_active=False)
            elif action == "enable_creative":
                cid = request.POST.get("creative_id")
                AdCreative.objects.filter(pk=cid).update(is_active=True)
            elif action == "save_placement":
                pid = request.POST.get("placement_id")
                fields = {
                    "name": (request.POST.get("name") or "")[:255],
                    "slug": (request.POST.get("slug") or "")[:255],
                    "page_context": (request.POST.get("page_context") or "")[:255],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if pid:
                    AdPlacement.objects.filter(pk=pid).update(**fields)
                else:
                    AdPlacement.objects.create(**fields)
                message = "Placement saved."
            elif action == "save_creative":
                cid = request.POST.get("creative_id")
                fields = {
                    "name": (request.POST.get("name") or "")[:255],
                    "creative_type": (request.POST.get("creative_type") or "")[:64],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if cid:
                    AdCreative.objects.filter(pk=cid).update(**fields)
                else:
                    AdCreative.objects.create(**fields)
                message = "Creative saved."
        except Exception as exc:
            logger.warning("Admin suite ads toggle/save failed: %s", exc)
            message = "Action failed."

    try:
        from django.utils import timezone

        from apps.ads.models import AdCreative, AdEvent, AdPlacement

        stats["placements"] = AdPlacement.objects.count()
        stats["creatives"] = AdCreative.objects.count()
        since = timezone.now() - timezone.timedelta(hours=24)
        stats["impressions_24h"] = AdEvent.objects.filter(
            event_type="impression", created_at__gte=since
        ).count()
        stats["clicks_24h"] = AdEvent.objects.filter(
            event_type="click", created_at__gte=since
        ).count()

        placement_qs = AdPlacement.objects.order_by("-updated_at")
        creative_qs = AdCreative.objects.order_by("-updated_at")
        if query:
            from django.db.models import Q

            placement_qs = placement_qs.filter(
                Q(name__icontains=query)
                | Q(slug__icontains=query)
                | Q(page_context__icontains=query)
            )
            creative_qs = creative_qs.filter(
                Q(name__icontains=query) | Q(creative_type__icontains=query)
            )

        placements = list(
            placement_qs[offset : offset + page_size].values(
                "id", "name", "slug", "page_context", "is_active", "updated_at"
            )
        )
        creatives = list(
            creative_qs[offset : offset + page_size].values(
                "id", "name", "creative_type", "is_active", "updated_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite ads snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ads.html",
        {
            "stats": stats,
            "placements": placements,
            "creatives": creatives,
            "message": message,
            "q": query,
            "page": page,
            "page_size": page_size,
        },
        nav_active="ads",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Marketing", "admin_suite:admin_suite_marketing"),
            ("Ads", None),
        ),
        subtitle="Placements, creatives, and 24h activity",
    )


@staff_member_required
def admin_suite_tags(request: HttpRequest) -> HttpResponse:
    """Tags read-only dashboard."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {"total": 0, "curated": 0, "deleted": 0}
    tags: list[Dict[str, Any]] = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 25
    if request.GET.get("refresh"):
        message = "Sitemap snapshot refreshed."
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            import nh3

            from apps.tags.models import Tag

            name = nh3.clean(request.POST.get("name", ""), tags=set())
            if action == "create" and name:
                Tag.objects.create(name=name)
                message = "Tag created."
            elif action == "update":
                tid = request.POST.get("tag_id")
                if tid and name:
                    Tag.objects.filter(pk=tid).update(name=name)
                    message = "Tag updated."
            elif action == "delete":
                tid = request.POST.get("tag_id")
                if tid:
                    Tag.objects.filter(pk=tid).update(is_deleted=True)
                    message = "Tag deleted."
        except Exception as exc:
            logger.warning("Admin suite tags action failed: %s", exc)
            message = "Action failed."

    try:
        from apps.tags.models import Tag

        stats["total"] = Tag.objects.count()
        stats["curated"] = Tag.objects.filter(is_curated=True).count()
        stats["deleted"] = Tag.objects.filter(is_deleted=True).count()
        qs = Tag.objects.filter(is_deleted=False).order_by("-usage_count", "name")
        if query:
            from django.db.models import Q

            qs = qs.filter(Q(name__icontains=query) | Q(slug__icontains=query))
        tags = list(
            qs[offset : offset + page_size].values(
                "id", "name", "slug", "usage_count", "is_curated"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite tags snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/tags.html",
        {
            "stats": stats,
            "tags": tags,
            "message": message,
            "page": page,
            "page_size": page_size,
            "q": query,
        },
        nav_active="tags",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Content", "admin_suite:admin_suite_content"),
            ("Tags", None),
        ),
        subtitle="Tag usage and curation status",
    )


@staff_member_required
def admin_suite_seo(request: HttpRequest) -> HttpResponse:
    """SEO dashboard: redirects and sitemap entries (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {"redirects": 0, "sitemap_urls": 0}
    redirects: list[Dict[str, Any]] = []
    sitemap_entries: list[Dict[str, Any]] = []
    seo_settings: Dict[str, Any] = {}
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 25
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.seo.models import Redirect, SitemapEntry
            from apps.seo.models_settings import SeoAutomationSettings

            if action == "disable_redirect":
                rid = request.POST.get("redirect_id")
                Redirect.objects.filter(pk=rid).update(is_active=False)
            elif action == "enable_redirect":
                rid = request.POST.get("redirect_id")
                Redirect.objects.filter(pk=rid).update(is_active=True)
            elif action == "disable_sitemap":
                sid = request.POST.get("sitemap_id")
                SitemapEntry.objects.filter(pk=sid).update(is_active=False)
            elif action == "enable_sitemap":
                sid = request.POST.get("sitemap_id")
                SitemapEntry.objects.filter(pk=sid).update(is_active=True)
            elif action == "save_redirect":
                rid = request.POST.get("redirect_id")
                data = {
                    "source": (request.POST.get("source") or "")[:255],
                    "target": (request.POST.get("target") or "")[:255],
                    "is_permanent": bool(request.POST.get("is_permanent")),
                    "is_active": bool(request.POST.get("is_active")),
                }
                if rid:
                    Redirect.objects.filter(pk=rid).update(**data)
                else:
                    Redirect.objects.create(**data)
                message = "Redirect saved."
            elif action == "save_seo_settings":
                cfg = SeoAutomationSettings.get_solo()
                bool_fields = [
                    "auto_meta",
                    "auto_tags",
                    "auto_schema",
                    "suggest_only",
                    "tag_sitemap_enabled",
                    "comment_nofollow",
                    "comment_bump_lastmod",
                ]
                for field in bool_fields:
                    setattr(cfg, field, bool(request.POST.get(field)))
                cfg.save()
                message = "SEO automation settings saved."
            # sitemap entries are auto-fed; no manual save in admin
        except Exception as exc:
            logger.warning("Admin suite seo toggle failed: %s", exc)
            message = "Action failed."

    try:
        from apps.seo.models import Redirect, SitemapEntry
        from apps.seo.models_settings import SeoAutomationSettings

        stats["redirects"] = Redirect.objects.count()
        stats["sitemap_urls"] = SitemapEntry.objects.count()
        redirect_qs = Redirect.objects.order_by("-updated_at")
        sitemap_qs = SitemapEntry.objects.order_by("-created_at")
        if query:
            from django.db.models import Q

            redirect_qs = redirect_qs.filter(
                Q(source__icontains=query) | Q(target__icontains=query)
            )
            sitemap_qs = sitemap_qs.filter(
                Q(url__icontains=query) | Q(changefreq__icontains=query)
            )

        redirects = list(
            redirect_qs[offset : offset + page_size].values(
                "id", "source", "target", "is_permanent", "is_active", "updated_at"
            )
        )
        sitemap_entries = list(
            sitemap_qs[offset : offset + page_size].values(
                "id", "url", "lastmod", "changefreq", "priority", "is_active"
            )
        )
        try:
            cfg = SeoAutomationSettings.get_solo()
            seo_settings = {
                "auto_meta": bool(getattr(cfg, "auto_meta", True)),
                "auto_tags": bool(getattr(cfg, "auto_tags", True)),
                "auto_schema": bool(getattr(cfg, "auto_schema", True)),
                "suggest_only": bool(getattr(cfg, "suggest_only", False)),
                "tag_sitemap_enabled": bool(getattr(cfg, "tag_sitemap_enabled", True)),
                "comment_nofollow": bool(getattr(cfg, "comment_nofollow", True)),
                "comment_bump_lastmod": bool(
                    getattr(cfg, "comment_bump_lastmod", True)
                ),
            }
        except Exception:
            seo_settings = {}
    except Exception as exc:
        logger.debug("Admin suite seo snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/seo.html",
        {
            "stats": stats,
            "redirects": redirects,
            "sitemap_entries": sitemap_entries,
            "seo_settings": seo_settings,
            "message": message,
            "q": query,
            "page": page,
            "page_size": page_size,
        },
        nav_active="seo",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Marketing", "admin_suite:admin_suite_marketing"),
            ("SEO", None),
        ),
        subtitle="Redirects and sitemap entries",
    )


@staff_member_required
def admin_suite_registry(request: HttpRequest) -> HttpResponse:
    """App registry flags (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    registry = {}
    try:
        from apps.core.models import AppRegistry

        reg = AppRegistry.get_solo()
        registry = reg.__dict__.copy()
        registry = {k: v for k, v in registry.items() if not k.startswith("_")}
    except Exception as exc:
        logger.debug("Admin suite app registry snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/registry.html",
        {
            "registry": registry,
        },
        nav_active="registry",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("App Registry", None)
        ),
        subtitle="App flags and feature registry (read-only snapshot)",
    )


@csrf_protect
@staff_member_required
def admin_suite_comments(request: HttpRequest) -> HttpResponse:
    """
    Comment moderation (staff-only). Supports POST actions: approve, reject, spam.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    action = request.POST.get("action") if request.method == "POST" else ""
    comment_id = request.POST.get("comment_id") if request.method == "POST" else None

    if (
        request.method == "POST"
        and comment_id
        and action in {"approve", "reject", "spam"}
    ):
        try:
            from apps.comments.models import Comment

            comment = Comment.objects.filter(pk=comment_id).first()
            if comment:
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
                message = f"Comment {comment_id} marked as {action}."
                logger.info(
                    "admin_suite_comment_action",
                    extra={
                        "comment_id": comment_id,
                        "action": action,
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
        except Exception as exc:
            logger.warning("Admin suite comment action failed: %s", exc)
            message = "Action failed."

    pending_comments: list[Dict[str, Any]] = []
    page = 1
    page_size = 25
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25

    try:
        from apps.comments.models import Comment

        offset = (page - 1) * page_size
        qs = Comment.objects.filter(status=Comment.Status.PENDING).order_by(
            "-created_at"
        )
        pending_comments = list(
            qs[offset : offset + page_size].values(
                "id", "user_id", "body", "created_at", "post_id"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite pending comments fetch failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/comments.html",
        {
            "pending_comments": pending_comments,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="comments",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Content", "admin_suite:content"),
            ("Comments", None),
        ),
        subtitle="Moderate pending comments",
    )


@csrf_protect
@staff_member_required
def admin_suite_pending_approval(request: HttpRequest) -> HttpResponse:
    """Items pending admin approval (users, comments, posts, etc.)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    pending_items = {
        "users": [],
        "comments": [],
        "posts": [],
    }

    # Pending user approvals
    try:
        pending_items["users"] = list(
            User.objects.filter(is_active=False, email_verified=False)
            .order_by("-date_joined")[:20]
            .values("id", "email", "first_name", "last_name", "date_joined")
        )
    except Exception as exc:
        logger.debug("Failed to fetch pending users: %s", exc)

    # Pending comments
    try:
        from apps.comments.models import Comment

        pending_items["comments"] = list(
            Comment.objects.filter(is_approved=False, is_spam=False)
            .order_by("-created_at")[:20]
            .values("id", "user_id", "body", "created_at", "post_id")
        )
    except Exception as exc:
        logger.debug("Failed to fetch pending comments: %s", exc)

    # Pending blog posts
    try:
        from apps.blog.models import Post

        pending_items["posts"] = list(
            Post.objects.filter(status="pending")
            .order_by("-created_at")[:20]
            .values("id", "title", "slug", "created_at", "author_id")
        )
    except Exception as exc:
        logger.debug("Failed to fetch pending posts: %s", exc)

    total_pending = sum(len(v) for v in pending_items.values())

    return _render_admin(
        request,
        "admin_suite/pending_approval.html",
        {
            "pending_items": pending_items,
            "total_pending": total_pending,
        },
        nav_active="dashboard",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Pending Approval", None),
        ),
        subtitle=f"{total_pending} item(s) pending approval",
    )


__all__ = [
    "admin_suite_pages",
    "admin_suite_blog",
    "admin_suite_content",
    "admin_suite_marketing",
    "admin_suite_ai",
    "admin_suite_ads",
    "admin_suite_tags",
    "admin_suite_seo",
    "admin_suite_registry",
    "admin_suite_comments",
    "admin_suite_pending_approval",
    "PageForm",
]
