from __future__ import annotations

from typing import Any, Dict, List


def navigation_pages(request) -> Dict[str, Any]:
    """
    Provide a lightweight list of published pages for the header.
    Kept small to avoid large DB hits and works without raising.
    """
    items: List[Dict[str, str]] = []
    exclude_slugs = {"privacy", "terms", "cookies"}
    try:
        from apps.pages.models import Page  # type: ignore

        qs = Page.objects.filter(status="published").exclude(slug__in=exclude_slugs)
        for p in qs.only("slug", "title")[:6]:
            items.append(
                {
                    "title": p.title or "Page",
                    "url": getattr(p, "get_absolute_url", lambda: f"/pages/{p.slug}/")(),
                }
            )
    except Exception:
        items = []
    return {"pages_nav": items}
