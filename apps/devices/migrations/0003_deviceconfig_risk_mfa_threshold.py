from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deviceconfig",
            name="risk_mfa_threshold",
            field=models.PositiveIntegerField(
                default=75,
                help_text="If a device risk score meets/exceeds this value, require MFA to continue.",
            ),
        ),
    ]
