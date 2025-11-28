# Generated manually to enhance Comment model with statuses/moderation fields.
from __future__ import annotations

from django.db import migrations, models
from django.utils import timezone


def seed_status(apps, schema_editor):
    Comment = apps.get_model("comments", "Comment")
    for c in Comment.objects.all():
        if not c.status:
            c.status = "approved" if getattr(c, "is_approved", False) else "pending"
            c.save(update_fields=["status"])


class Migration(migrations.Migration):
    dependencies = [
        ("comments", "0002_comment_threading_and_meta"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="comment",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="comment",
            name="moderation_flags",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="comment",
            name="status",
            field=models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("spam", "Spam")], db_index=True, default="pending", max_length=20),
        ),
        migrations.AddField(
            model_name="comment",
            name="toxicity_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="comment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(seed_status, reverse_code=migrations.RunPython.noop),
    ]
