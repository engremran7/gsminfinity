from __future__ import annotations

from typing import Dict, Type

from django.contrib.sitemaps import Sitemap

from .sitemaps import PublishedPagesSitemap

_REGISTRY: Dict[str, Type[Sitemap]] = {
    "pages": PublishedPagesSitemap,
}


def register_sitemap(name: str, sitemap_cls: Type[Sitemap]) -> None:
    """
    Register an additional Sitemap class for inclusion in sitemap.xml/index.
    Designed to allow other apps to plug in without tight coupling.
    """
    if not name or not sitemap_cls:
        return
    _REGISTRY[name] = sitemap_cls


def get_sitemaps() -> Dict[str, Type[Sitemap]]:
    return dict(_REGISTRY)
