from __future__ import annotations

from django.db import models
from solo.models import SingletonModel


class SeoAutomationSettings(SingletonModel):
    """
    Site-wide SEO automation settings.
    Keeps automation self-contained in the SEO app.
    """

    auto_meta = models.BooleanField(
        default=True,
        help_text="Auto-generate meta title/description/canonical when missing.",
    )
    auto_tags = models.BooleanField(
        default=True,
        help_text="Auto-extract tags from title/summary/body and attach to posts.",
    )
    auto_schema = models.BooleanField(
        default=True, help_text="Generate JSON-LD (Article/Breadcrumb) for posts."
    )
    suggest_only = models.BooleanField(
        default=False, help_text="If true, only suggest tags; do not auto-attach."
    )
    tag_sitemap_enabled = models.BooleanField(
        default=True, help_text="Expose tag sitemap section when tags are public."
    )
    comment_nofollow = models.BooleanField(
        default=True, help_text="Add rel='nofollow ugc' to comment links."
    )
    comment_bump_lastmod = models.BooleanField(
        default=True, help_text="Update lastmod for posts/pages when new comments land."
    )

    class Meta:
        verbose_name = "SEO Automation Settings"
        db_table = "seo_seoautomationsettings"

    def __str__(self) -> str:
        return "SEO Automation Settings"


# Backwards-compatible alias (does not register a second model)
SeoSettings = SeoAutomationSettings
