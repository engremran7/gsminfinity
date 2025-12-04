from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_userssettings_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="username_changes_this_year",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="customuser",
            name="username_last_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
