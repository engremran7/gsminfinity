from __future__ import annotations

from django.contrib.sitemaps.views import index, sitemap
from django.contrib.sites.models import Site
from django.http import Http404
from django.template.response import TemplateResponse

from apps.site_settings.models import SiteSettings

from .sitemap_registry import get_sitemaps


def sitemap_index_view(request):
    settings = SiteSettings.get_solo()
    if not getattr(settings, "sitemap_index_enabled", False):
        raise Http404()
    return index(
        request,
        sitemaps=get_sitemaps(),
        sitemap_url_name="pages:sitemap_section",
        template_name="sitemap_index.xml",
        extra_context={"xsl_url": "/static/xsl/sitemap.xsl"},
    )


def sitemap_view(request):
    """
    Backwards-compatible endpoint for /sitemap.xml, now serving the sitemap index.
    """
    settings = SiteSettings.get_solo()
    if not getattr(settings, "sitemap_index_enabled", False):
        raise Http404()
    return index(
        request,
        sitemaps=get_sitemaps(),
        sitemap_url_name="pages:sitemap_section",
    )


def sitemap_section_view(request, section):
    settings = SiteSettings.get_solo()
    if not getattr(settings, "sitemap_enabled", False):
        raise Http404()
    sitemaps = get_sitemaps()
    if section not in sitemaps:
        raise Http404()
    return sitemap(request, sitemaps=sitemaps, section=section)


def sitemap_all_view(request):
    """
    Aggregate all sitemap sections into a single urlset for consumers that prefer one file.
    Still honors enable/disable toggles.
    """
    settings = SiteSettings.get_solo()
    if not getattr(settings, "sitemap_enabled", False):
        raise Http404()

    sitemaps = get_sitemaps()
    host = request.get_host() or ""
    protocol = "https" if getattr(settings, "force_https", False) else request.scheme or "http"
    # Use runtime host to avoid default example.com during local/dev usage
    site = Site(domain=host, name=host) if host else Site.objects.get_current()
    urls = []
    # instantiate and merge urls from each sitemap
    for sm in sitemaps.values():
        try:
            sm_instance = sm()
            urls.extend(
                sm_instance.get_urls(
                    site=site,
                    protocol=getattr(sm_instance, "protocol", None) or protocol,
                )
            )
        except Exception:
            continue

    return TemplateResponse(
        request,
        "sitemap.xml",
        {"urlset": urls, "xsl_url": "/static/xsl/sitemap.xsl"},
        content_type="application/xml",
    )
