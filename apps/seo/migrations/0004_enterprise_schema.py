# Generated manually to align SEO models with enterprise spec.
from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def migrate_metadata_fields(apps, schema_editor):
    Metadata = apps.get_model("seo", "Metadata")
    for meta in Metadata.objects.all():
        # Preserve existing values into new fields.
        meta.meta_title = getattr(meta, "title", "") or ""
        meta.meta_description = getattr(meta, "description", "") or ""
        old_keywords = getattr(meta, "keywords", "") or ""
        if old_keywords and isinstance(old_keywords, str):
            parts = [p.strip() for p in old_keywords.split(",") if p.strip()]
            if parts:
                meta.focus_keywords = parts
        meta.social_image = getattr(meta, "og_image", "") or ""
        if not meta.generated_at:
            meta.generated_at = timezone.now()
        meta.save(
            update_fields=[
                "meta_title",
                "meta_description",
                "focus_keywords",
                "social_image",
                "generated_at",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("seo", "0003_metadata_ai_score_metadata_focus_keywords_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # SEOModel audit/soft-delete fields
        migrations.AddField(
            model_name="seomodel",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="seomodel",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="seomodel_created",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="seomodel",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="seomodel",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="seomodel_deleted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="seomodel",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="seomodel",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="seomodel_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Metadata new fields
        migrations.AddField(
            model_name="metadata",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="metadata",
            name="generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="metadata",
            name="meta_description",
            field=models.CharField(blank=True, default="", max_length=320),
        ),
        migrations.AddField(
            model_name="metadata",
            name="meta_title",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="metadata",
            name="schema_json",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="metadata",
            name="social_image",
            field=models.URLField(blank=True, default=""),
        ),
        # SchemaEntry / SitemapEntry / Redirect tracking fields
        migrations.AddField(
            model_name="schemaentry",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="schemaentry",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="sitemapentry",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="redirect",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        # LinkableEntity enhancements
        migrations.AddField(
            model_name="linkableentity",
            name="aliases",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="linkableentity",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="linkableentity",
            name="entity_type",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="linkableentity",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="linkableentity",
            name="slug",
            field=models.SlugField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="linkableentity",
            name="vector",
            field=models.BinaryField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="linkableentity",
            name="keywords",
            field=models.JSONField(blank=True, default=list),
        ),
        # LinkSuggestion enhancements
        migrations.AddField(
            model_name="linksuggestion",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="linksuggestion",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        # Metadata data migration then drop legacy fields
        migrations.RunPython(migrate_metadata_fields, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(model_name="metadata", name="description"),
        migrations.RemoveField(model_name="metadata", name="keywords"),
        migrations.RemoveField(model_name="metadata", name="og_image"),
        migrations.RemoveField(model_name="metadata", name="title"),
    ]
