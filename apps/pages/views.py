from __future__ import annotations

import logging

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.site_settings.models import SiteSettings

from .models import Page

logger = logging.getLogger(__name__)


def _resolve_page(slug: str | None) -> Page:
    if not slug:
        slug = "home"
    try:
        page = Page.objects.filter(slug=slug).first()
    except Exception as exc:
        logger.warning("Page lookup failed for %s: %s", slug, exc)
        page = None

    # Note: "home" slug is NOT auto-created here because the homepage
    # is handled by home_landing view at root URL, not by pages app
    if not page or not page.is_published:
        raise Http404()
    now = timezone.now()
    if page.unpublish_at and page.unpublish_at <= now:
        raise Http404()
    return page


@require_GET
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


@require_GET
def home_landing(request: HttpRequest) -> HttpResponse:
    """
    Enhanced homepage with dual-column layout displaying:
    - Stats: Brands, Models, Firmwares, Downloads, Auto/Manual Blogs
    - Search bar for quick navigation
    - Latest/trending firmwares
    - Latest/trending blog posts
    - Most requested firmwares
    - Auto-managed ad placements

    Optimized with caching via HomePageWidgetService
    """
    from django.apps import apps
    from django.db.models import Sum

    from .widgets import HomePageWidgetService

    # Get stats for homepage
    stats = {
        "brands_count": 0,
        "models_count": 0,
        "firmwares_count": 0,
        "total_downloads": 0,
        "auto_blogs_count": 0,
        "manual_blogs_count": 0,
    }

    try:
        # Firmware stats
        if apps.is_installed("apps.firmwares"):
            Brand = apps.get_model("firmwares", "Brand")
            Model = apps.get_model("firmwares", "Model")
            OfficialFirmware = apps.get_model("firmwares", "OfficialFirmware")
            EngineeringFirmware = apps.get_model("firmwares", "EngineeringFirmware")
            ReadbackFirmware = apps.get_model("firmwares", "ReadbackFirmware")
            ModifiedFirmware = apps.get_model("firmwares", "ModifiedFirmware")
            OtherFirmware = apps.get_model("firmwares", "OtherFirmware")

            # Brand doesn't have is_active, count all brands
            stats["brands_count"] = Brand.objects.count()
            stats["models_count"] = Model.objects.filter(is_active=True).count()

            # Count all active firmwares
            stats["firmwares_count"] = sum(
                [
                    OfficialFirmware.objects.filter(is_active=True).count(),
                    EngineeringFirmware.objects.filter(is_active=True).count(),
                    ReadbackFirmware.objects.filter(is_active=True).count(),
                    ModifiedFirmware.objects.filter(is_active=True).count(),
                    OtherFirmware.objects.filter(is_active=True).count(),
                ]
            )

            # Total downloads across all firmware types
            total_downloads = 0
            for fw_model in [
                OfficialFirmware,
                EngineeringFirmware,
                ReadbackFirmware,
                ModifiedFirmware,
                OtherFirmware,
            ]:
                downloads = fw_model.objects.filter(is_active=True).aggregate(
                    total=Sum("download_count")
                )["total"]
                if downloads:
                    total_downloads += downloads
            stats["total_downloads"] = total_downloads

        # Blog stats
        if apps.is_installed("apps.blog"):
            Post = apps.get_model("blog", "Post")
            stats["auto_blogs_count"] = Post.objects.filter(
                is_published=True, is_ai_generated=True
            ).count()
            stats["manual_blogs_count"] = Post.objects.filter(
                is_published=True, is_ai_generated=False
            ).count()

    except Exception as e:
        logger.warning(f"Error fetching homepage stats: {e}")

    # Get all widget data in single optimized call
    widget_config = {
        "latest_firmwares": 8,  # Left column
        "trending_firmwares": 8,  # Left column
        "most_requested": 8,  # Left column
        "latest_blogs": 6,  # Right column
        "trending_blogs": 6,  # Right column
        "layout": "dual_column",
    }

    homepage_data = HomePageWidgetService.get_homepage_data(widget_config)

    # Organize into left/right columns for template
    context = {
        "stats": stats,
        "left_column": {
            "latest_firmwares": homepage_data["latest_firmwares"],
            "trending_firmwares": homepage_data["trending_firmwares"],
            "most_requested": homepage_data["most_requested_firmwares"],
        },
        "right_column": {
            "latest_blogs": homepage_data["latest_blogs"],
            "trending_blogs": homepage_data["trending_blogs"],
        },
        "ad_placements": homepage_data["ad_placements"],
        "cache_timestamp": homepage_data.get("cache_timestamp"),
    }

    return render(
        request,
        "pages/home_landing.html",
        context,
    )


@require_GET
def robots_txt(request: HttpRequest) -> HttpResponse:
    """
    Simple robots.txt that points to the hybrid sitemap and disallows admin/sensitive paths.
    """
    return render(request, "robots.txt", content_type="text/plain")
