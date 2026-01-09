from __future__ import annotations

from apps.seo.models import SitemapEntry


def crawl_stub(urls: list[str]):
    """
    Placeholder for internal crawler; marks URLs in sitemap.
    """
    for url in urls:
        SitemapEntry.objects.update_or_create(url=url, defaults={"is_active": True})
