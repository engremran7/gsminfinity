
from __future__ import annotations

from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(field, css: str = ""):
    """
    Append CSS classes to a form field widget safely.
    """
    try:
        existing = field.field.widget.attrs.get("class", "")
        combined = f"{existing} {css}".strip()
        return field.as_widget(attrs={"class": combined})
    except Exception:
        return field


