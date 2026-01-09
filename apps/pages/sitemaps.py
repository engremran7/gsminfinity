from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils import timezone

from apps.site_settings.models import SiteSettings

from .models import Page


class PublishedPagesSitemap(Sitemap):
    """
    Enterprise-grade sitemap with per-page changefreq/priority, protocol awareness,
    canonical URL support, and optional page-size capping.
    """

    def __init__(self):
        super().__init__()
        try:
            ss = SiteSettings.get_solo()
        except Exception:
            ss = None
        self._page_size = getattr(ss, "sitemap_page_size", None) or None
        force_https = bool(getattr(ss, "force_https", False))
        self.protocol = "https" if force_https else "http"

    def items(self):
        now = timezone.now()
        qs = (
            Page.objects.filter(status="published", access_level="public", include_in_sitemap=True)
            .exclude(unpublish_at__isnull=False, unpublish_at__lte=now)
            .order_by("-last_modified")
        )
        if self._page_size:
            try:
                return list(qs[: int(self._page_size)])
            except Exception:
                return list(qs)
        return list(qs)

    def lastmod(self, obj: Page):
        return obj.last_modified or obj.publish_at

    def location(self, obj: Page):
        if getattr(obj, "canonical_url", ""):
            return obj.canonical_url
        return reverse("pages:page", kwargs={"slug": obj.slug})

    def changefreq(self, obj: Page):
        return obj.changefreq

    def priority(self, obj: Page):
        try:
            return float(obj.priority)
        except Exception:
            return 0.5

    def get_urls(self, page=1, site=None, protocol=None):
        site = site or Site.objects.get_current()
        protocol = protocol or self.protocol or "https"
        return super().get_urls(page=page, site=site, protocol=protocol)


class StaticViewsSitemap(Sitemap):
    """
    Includes key static views that are not part of the Page model (e.g., auth, dashboard).
    Keeps the list centralized and guarded by reverse() lookups so missing routes are skipped.
    """

    changefreq = "weekly"
    priority = 0.4

    def __init__(self):
        super().__init__()
        try:
            ss = SiteSettings.get_solo()
        except Exception:
            ss = None
        force_https = bool(getattr(ss, "force_https", False))
        self.protocol = "https" if force_https else "http"

    def items(self):
        # Tuple of (view_name, kwargs)
        candidates = [
            ("home", None),
            ("blog:post_list", None),
            ("users:dashboard", None),
            ("account_login", None),
            ("account_signup", None),
            ("account_change_password", None),
            ("account_reset_password", None),
        ]
        resolved: list[tuple[str, dict | None]] = []
        for name, kwargs in candidates:
            try:
                # Validate that reverse works; discard missing routes
                reverse(name, kwargs=kwargs) if kwargs else reverse(name)
                resolved.append((name, kwargs))
            except Exception:
                continue
        return resolved

    def location(self, item):
        name, kwargs = item
        try:
            return reverse(name, kwargs=kwargs) if kwargs else reverse(name)
        except Exception:
            return ""

    def lastmod(self, obj):
        return None
