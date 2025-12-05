from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("devices", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserDeviceQuota",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("max_devices", models.PositiveIntegerField(blank=True, help_text="Override max devices; null = default", null=True)),
                ("window", models.CharField(choices=[("3m", "3 Months"), ("6m", "6 Months"), ("12m", "12 Months")], default="6m", max_length=4)),
                ("last_reset_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("notes", models.TextField(blank=True, default="")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="device_quotas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "User Device Quota",
                "verbose_name_plural": "User Device Quotas",
            },
        ),
        migrations.AddIndex(
            model_name="userdevicequota",
            index=models.Index(fields=["user"], name="devices_user_idx"),
        ),
    ]
