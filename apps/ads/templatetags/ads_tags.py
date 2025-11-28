from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from apps.ads.models import AdPlacement
from apps.core.cache import cache
from apps.core.utils import feature_flags
from apps.site_settings.models import SiteSettings

register = template.Library()


def _ads_enabled() -> bool:
    try:
        ss = SiteSettings.get_solo()
        return bool(getattr(ss, "ads_enabled", False))
    except Exception:
        return False


@register.simple_tag(takes_context=True)
def render_ad_slot(context, slug: str, allowed_types: str = "", allowed_sizes: str = ""):
    """
    Render an ad slot placeholder. Uses placement config when ads are enabled.
    Respects site feature flags and consent (if present on request).
    """
    if not _ads_enabled() or not feature_flags.ads_enabled():
        return ""

    request = context.get("request")
    consent_flags = getattr(request, "consent_flags", None)
    if consent_flags is not None:
        try:
            if not getattr(consent_flags, "allow_ads", True):
                return ""
        except Exception:
            pass

    cache_key = f"ads_slot_{slug}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    placement = AdPlacement.objects.filter(slug=slug, is_active=True, is_enabled=True, is_deleted=False).first()
    html = render_to_string(
        "ads/components/slot.html",
        {
            "placement": placement,
            "fallback_slug": slug,
            "allowed_types": allowed_types or getattr(placement, "allowed_types", ""),
            "allowed_sizes": allowed_sizes or getattr(placement, "allowed_sizes", ""),
        },
        request=context.get("request"),
    )
    safe_html = mark_safe(html)
    cache.set(cache_key, safe_html, 120)
    return safe_html


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None
