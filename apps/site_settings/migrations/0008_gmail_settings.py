from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("site_settings", "0007_pages_sitemap_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="gmail_app_password",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Gmail app password (never store your real password).",
                max_length=128,
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="gmail_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Use Gmail SMTP with an app password (recommended). When disabled, falls back to environment settings.",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="gmail_from_email",
            field=models.EmailField(
                blank=True,
                default="",
                help_text="Optional From header. Defaults to gmail_username when empty.",
                max_length=254,
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="gmail_username",
            field=models.EmailField(
                blank=True,
                default="",
                help_text="Gmail address used for SMTP AUTH.",
                max_length=254,
            ),
        ),
    ]

