from __future__ import annotations

import logging

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.site_settings.models import SiteSettings
from .models import Page

logger = logging.getLogger(__name__)


def _resolve_page(slug: str | None) -> Page:
    if not slug:
        slug = "home"
    page = Page.objects.filter(slug=slug).first()
    if not page and slug == "home":
        # Auto-bootstrap a home page if missing to avoid 404s in fresh envs
        page = Page.objects.create(
            slug="home",
            title="Home",
            content="Welcome",
            status="published",
            access_level="public",
            include_in_sitemap=True,
        )
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


def robots_txt(request: HttpRequest) -> HttpResponse:
    """
    Simple robots.txt that points to the hybrid sitemap and disallows admin/sensitive paths.
    """
    return render(request, "robots.txt", content_type="text/plain")
