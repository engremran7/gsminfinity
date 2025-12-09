from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_securityquestion"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]
