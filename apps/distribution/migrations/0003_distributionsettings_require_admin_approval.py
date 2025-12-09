from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("distribution", "0002_distribution_settings_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="distributionsettings",
            name="require_admin_approval",
            field=models.BooleanField(
                default=False,
                help_text="Require admin approval before executing queued jobs.",
            ),
        ),
    ]
