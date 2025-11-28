from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="enable_tenants",
            field=models.BooleanField(
                default=False,
                help_text="Enable public tenants listing when true.",
            ),
        ),
    ]
