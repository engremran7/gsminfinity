from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("distribution", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="distributionsettings",
            name="allow_indexing_jobs",
            field=models.BooleanField(
                default=False,
                help_text="Allow search engine indexing submit jobs (Google/Bing).",
            ),
        ),
        migrations.AddField(
            model_name="distributionsettings",
            name="auto_fanout_on_publish",
            field=models.BooleanField(
                default=True,
                help_text="Automatically queue distribution when a post is published.",
            ),
        ),
        migrations.AddField(
            model_name="distributionsettings",
            name="default_channels",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Optional override for enabled channels (empty = all supported).",
            ),
        ),
        migrations.AddField(
            model_name="distributionsettings",
            name="max_retries",
            field=models.PositiveIntegerField(
                default=3,
                help_text="Maximum retry attempts per job before marking as failed.",
            ),
        ),
        migrations.AddField(
            model_name="distributionsettings",
            name="retry_backoff_seconds",
            field=models.PositiveIntegerField(
                default=1800,
                help_text="Minimum age (seconds) before retrying a failed job.",
            ),
        ),
    ]
