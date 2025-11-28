from django.db import migrations, models


def populate_normalized(apps, schema_editor):
    Tag = apps.get_model("tags", "Tag")
    for tag in Tag.objects.all():
        tag.normalized_name = (tag.name or "").lower().strip()
        tag.usage_count = tag.posts.count() if hasattr(tag, "posts") else 0
        tag.save(update_fields=["normalized_name", "usage_count"])


class Migration(migrations.Migration):

    dependencies = [
        ("tags", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="tag",
            name="normalized_name",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="tag",
            name="usage_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(populate_normalized, migrations.RunPython.noop),
    ]
