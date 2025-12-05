from django.db import migrations, models
import django.db.models.deletion
import solo.models


class Migration(migrations.Migration):
    """
    Introduce automation-specific SEO settings in their own table to avoid clashing
    with the public SEOSettings feature-flag singleton.
    """

    dependencies = [
        ("seo", "0004_enterprise_schema"),
    ]

    operations = [
        migrations.CreateModel(
            name="SeoAutomationSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "auto_meta",
                    models.BooleanField(
                        default=True,
                        help_text="Auto-generate meta title/description/canonical when missing.",
                    ),
                ),
                (
                    "auto_tags",
                    models.BooleanField(
                        default=True,
                        help_text="Auto-extract tags from title/summary/body and attach to posts.",
                    ),
                ),
                (
                    "auto_schema",
                    models.BooleanField(
                        default=True,
                        help_text="Generate JSON-LD (Article/Breadcrumb) for posts.",
                    ),
                ),
                (
                    "suggest_only",
                    models.BooleanField(
                        default=False,
                        help_text="If true, only suggest tags; do not auto-attach.",
                    ),
                ),
                (
                    "tag_sitemap_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Expose tag sitemap section when tags are public.",
                    ),
                ),
                (
                    "comment_nofollow",
                    models.BooleanField(
                        default=True,
                        help_text="Add rel='nofollow ugc' to comment links.",
                    ),
                ),
                (
                    "comment_bump_lastmod",
                    models.BooleanField(
                        default=True,
                        help_text="Update lastmod for posts/pages when new comments land.",
                    ),
                ),
            ],
            options={
                "verbose_name": "SEO Automation Settings",
                "db_table": "seo_seoautomationsettings",
            },
            bases=(solo.models.SingletonModel, models.Model),
        ),
    ]
