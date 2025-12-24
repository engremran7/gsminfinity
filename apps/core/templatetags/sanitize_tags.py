"""
Template tags for HTML sanitization.

Usage in templates:
    {% load sanitize_tags %}
    
    {{ ad_code|sanitize_ad }}
    {{ cms_content|sanitize_html }}
    {{ user_text|sanitize_text }}
"""
from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

from apps.core.sanitizers import (
    sanitize_ad_code,
    sanitize_html_content,
    sanitize_plain_text,
)

register = template.Library()


@register.filter(name='sanitize_ad')
def sanitize_ad_filter(value: str) -> str:
    """
    Sanitize ad code HTML, allowing only safe ad-related tags and attributes.
    
    Usage:
        {{ slot.ad_unit.code|sanitize_ad }}
    """
    if not value:
        return ''
    return mark_safe(sanitize_ad_code(str(value)))


@register.filter(name='sanitize_html')
def sanitize_html_filter(value: str) -> str:
    """
    Sanitize CMS/blog HTML content, allowing rich formatting but removing XSS vectors.
    
    Usage:
        {{ page.content|sanitize_html }}
        {{ post.body|sanitize_html }}
    """
    if not value:
        return ''
    return mark_safe(sanitize_html_content(str(value)))


@register.filter(name='sanitize_text')
def sanitize_text_filter(value: str) -> str:
    """
    Strip all HTML from text, returning plain text only.
    
    Usage:
        {{ comment.body|sanitize_text }}
    """
    if not value:
        return ''
    return sanitize_plain_text(str(value))
