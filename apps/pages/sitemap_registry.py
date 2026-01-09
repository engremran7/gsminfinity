from __future__ import annotations

from django.contrib.sitemaps import Sitemap

from .sitemaps import PublishedPagesSitemap

_REGISTRY: dict[str, type[Sitemap]] = {
    "pages": PublishedPagesSitemap,
}


def register_sitemap(name: str, sitemap_cls: type[Sitemap]) -> None:
    """
    Register an additional Sitemap class for inclusion in sitemap.xml/index.
    Designed to allow other apps to plug in without tight coupling.
    """
    if not name or not sitemap_cls:
        return
    _REGISTRY[name] = sitemap_cls


def get_sitemaps() -> dict[str, type[Sitemap]]:
    return dict(_REGISTRY)
