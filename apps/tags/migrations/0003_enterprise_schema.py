# Generated manually to enhance Tag model to enterprise spec.
from __future__ import annotations

from django.db import migrations, models
from django.utils import timezone


def backfill_normalized_and_slug(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")
    for tag in Tag.objects.all():
        changed = False
        if not tag.normalized_name and tag.name:
            tag.normalized_name = tag.name.lower().strip()
            changed = True
        if not tag.slug and tag.name:
            from django.utils.text import slugify

            tag.slug = slugify(tag.name)[:75]
            changed = True
        if changed:
            tag.save(update_fields=["normalized_name", "slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("tags", "0002_tag_normalized_description_usage"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="ai_suggested",
            field=models.BooleanField(default=False, help_text="True if suggested by AI and not yet curated."),
        ),
        migrations.AddField(
            model_name="tag",
            name="co_occurrence",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="tag",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tag",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="tag",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tag",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="tag",
            name="synonyms",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="tag",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_normalized_and_slug, reverse_code=migrations.RunPython.noop),
    ]
