from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0006_post_indexes_validators"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="ai_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="post",
            name="ai_run_id",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="post",
            name="is_ai_generated",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="post",
            name="allow_comments",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="post",
            name="noindex",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="AutoTopic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(max_length=240)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("succeeded", "Succeeded"), ("failed", "Failed")], default="queued", max_length=20)),
                ("ai_run_id", models.CharField(blank=True, default="", max_length=100)),
                ("last_error", models.TextField(blank=True, default="")),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("post", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="blog.post")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="autotopic",
            index=models.Index(fields=["status"], name="blog_autotopic_status_idx"),
        ),
    ]
