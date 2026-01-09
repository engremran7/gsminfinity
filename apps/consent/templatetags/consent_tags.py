from django import template

register = template.Library()


@register.filter
def replace_underscores(value: str, replacement: str = " ") -> str:
    """
    Safe underscore replacement for template usage.
    """
    try:
        return str(value).replace("_", replacement)
    except Exception:
        return value


@register.filter
def format_categories(categories: dict) -> str:
    """
    Render categories dict as a human-readable list of enabled items.
    """
    if not categories:
        return "Functional (required)"
    enabled = [replace_underscores(k) for k, v in categories.items() if v]
    if not enabled:
        return "Functional (required)"
    return ", ".join(enabled)
