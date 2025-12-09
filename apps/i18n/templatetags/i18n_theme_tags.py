
from __future__ import annotations

from django import template

from apps.i18n.models import Locale

register = template.Library()


@register.simple_tag
def get_i18n_locales():
    """
    Return enabled locales for switcher rendering.
    """
    return Locale.objects.filter(enabled_global=True).order_by("code")


