from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0007_post_ai_fields_autotopic"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="blog.category",
                help_text="Optional parent to build nested categories (e.g., AI > Safety).",
            ),
        ),
        migrations.AddIndex(
            model_name="category",
            index=models.Index(fields=["parent", "name"], name="category_parent_name_idx"),
        ),
    ]
