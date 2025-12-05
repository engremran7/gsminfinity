from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.utils import timezone

from apps.site_settings.models import SiteSettings

from .models import SitemapEntry


class ActiveSeoEntriesSitemap(Sitemap):
    """
    Sitemap that surfaces active SEO-tracked URLs from the SEO module.
    Useful for non-page assets or external URLs we still want crawled.
    """

    def __init__(self):
        super().__init__()
        try:
            ss = SiteSettings.get_solo()
        except Exception:
            ss = None
        force_https = bool(getattr(ss, "force_https", False))
        self.protocol = "https" if force_https else "http"
        self._site_domain = getattr(Site.objects.get_current(), "domain", "")

    def items(self):
        return (
            SitemapEntry.objects.filter(is_active=True)
            .order_by("-lastmod", "-created_at")
            .only("url", "lastmod", "changefreq", "priority")
        )

    def lastmod(self, obj: SitemapEntry):
        return obj.lastmod or timezone.now()

    def location(self, obj: SitemapEntry):
        url = obj.url
        if self._site_domain and url.startswith("/"):
            return f"{self.protocol}://{self._site_domain}{url}"
        return url

    def changefreq(self, obj: SitemapEntry):
        return obj.changefreq or "weekly"

    def priority(self, obj: SitemapEntry):
        try:
            return float(obj.priority)
        except (TypeError, ValueError):
            return 0.5
