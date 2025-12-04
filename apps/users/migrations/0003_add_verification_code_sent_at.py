from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_customuser_manual_signup"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="verification_code_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
