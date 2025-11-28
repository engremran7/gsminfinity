from __future__ import annotations

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType

from apps.core.utils import feature_flags
from apps.site_settings.models import SiteSettings
from apps.seo.models import SEOModel, Metadata, SchemaEntry

register = template.Library()


def _seo_enabled() -> bool:
    if not feature_flags.seo_enabled():
        return False
    try:
        ss = SiteSettings.get_solo()
        return bool(getattr(ss, "seo_enabled", False))
    except Exception:
        return False


@register.simple_tag(takes_context=True)
def render_seo_meta(context, obj):
    """
    Render SEO meta/OG/JSON-LD for an object if enabled and metadata exists.
    """
    if not _seo_enabled() or obj is None:
        return ""
    try:
        ct = ContentType.objects.get_for_model(obj.__class__)
        seo_obj = SEOModel.objects.filter(content_type=ct, object_id=obj.pk).first()
    except Exception:
        seo_obj = None
    if not seo_obj or not hasattr(seo_obj, "metadata"):
        return ""
    meta: Metadata = seo_obj.metadata
    schemas = SchemaEntry.objects.filter(seo=seo_obj, locked=False)
    html = render_to_string(
        "seo/components/meta.html",
        {"meta": meta, "schemas": schemas},
        request=context.get("request"),
    )
    return mark_safe(html)


@register.simple_tag
def seo_redirect(path: str):
    """
    Returns a Redirect target if there is an active redirect for the given path.
    """
    if not feature_flags.seo_enabled():
        return None
    from apps.seo.models import Redirect  # lazy import to avoid cycles

    try:
        redirect = Redirect.objects.filter(source=path, is_active=True).first()
        return redirect.target if redirect else None
    except Exception:
        return None
