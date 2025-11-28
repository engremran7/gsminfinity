from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="canonical_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="post",
            name="featured",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="post",
            name="hero_image",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="post",
            name="publish_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="post",
            name="reading_time",
            field=models.PositiveIntegerField(default=0, help_text="Minutes"),
        ),
        migrations.AddField(
            model_name="post",
            name="seo_description",
            field=models.CharField(blank=True, default="", max_length=320),
        ),
        migrations.AddField(
            model_name="post",
            name="seo_title",
            field=models.CharField(blank=True, default="", max_length=240),
        ),
        migrations.AddField(
            model_name="post",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("scheduled", "Scheduled"),
                    ("published", "Published"),
                    ("archived", "Archived"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="post",
            name="version",
            field=models.PositiveIntegerField(default=1),
        ),
    ]
