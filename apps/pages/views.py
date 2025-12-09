from __future__ import annotations

import logging

from django.db import connection
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.site_settings.models import SiteSettings
from .models import Page

logger = logging.getLogger(__name__)


class _FallbackPage:
    slug = "home"
    title = "Home"
    content = "Welcome"
    content_format = "html"
    access_level = "public"
    publish_at = None
    unpublish_at = None

    @property
    def is_published(self) -> bool:
        return True


def _page_table_exists() -> bool:
    try:
        return Page._meta.db_table in connection.introspection.table_names()
    except Exception:
        return False


def _resolve_page(slug: str | None) -> Page:
    if not slug:
        slug = "home"
    try:
        page = Page.objects.filter(slug=slug).first()
    except Exception as exc:
        logger.warning("Page lookup failed for %s: %s", slug, exc)
        page = None

    if not page and slug == "home":
        # Only attempt auto-bootstrap when the table exists and we can write.
        if _page_table_exists():
            try:
                page = Page.objects.create(
                    slug="home",
                    title="Home",
                    content="Welcome",
                    status="published",
                    access_level="public",
                    include_in_sitemap=True,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Home page bootstrap skipped: %s", exc)
        if not page:
            return _FallbackPage()

    if not page or not page.is_published:
        raise Http404()
    now = timezone.now()
    if page.unpublish_at and page.unpublish_at <= now:
        raise Http404()
    return page


def page_detail(request: HttpRequest, slug: str | None = None) -> HttpResponse:
    settings = SiteSettings.get_solo()
    if not getattr(settings, "pages_enabled", True):
        raise Http404()

    page = _resolve_page(slug)

    if page.access_level == "auth" and not request.user.is_authenticated:
        raise Http404()
    if page.access_level == "staff" and not getattr(request.user, "is_staff", False):
        raise Http404()

    template_name = "pages/page.html"
    context = {
        "page": page,
    }
    return render(request, template_name, context)


def home_landing(request: HttpRequest) -> HttpResponse:
    """
    Minimal landing page that points visitors to the latest blog posts.
    Shows only a small set of links until more pages are published.
    """
    latest_posts = []
    try:
        from apps.blog.models import Post  # type: ignore

        latest_posts = list(
            Post.objects.filter(is_published=True)
            .order_by("-published_at")[:4]
            .values("id", "title", "slug", "summary", "published_at")
        )
    except Exception:
        latest_posts = []

    return render(
        request,
        "pages/home_landing.html",
        {"latest_posts": latest_posts},
    )


def robots_txt(request: HttpRequest) -> HttpResponse:
    """
    Simple robots.txt that points to the hybrid sitemap and disallows admin/sensitive paths.
    """
    return render(request, "robots.txt", content_type="text/plain")
