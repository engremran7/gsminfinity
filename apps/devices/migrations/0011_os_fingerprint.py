from __future__ import annotations

from django.db import migrations, models


def backfill_os_fingerprint(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    for d in Device.objects.all():
        if not getattr(d, "os_fingerprint", None):
            seed = getattr(d, "hardware_uuid", "") or getattr(d, "device_key_id", "") or str(d.id)
            d.os_fingerprint = seed
            d.save(update_fields=["os_fingerprint"])


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0010_device_keys"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="os_fingerprint",
            field=models.CharField(db_index=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="device",
            name="os_name",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="device",
            name="os_version",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.RunPython(backfill_os_fingerprint, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="device",
            unique_together={("user", "os_fingerprint")},
        ),
        migrations.AddIndex(
            model_name="device",
            index=models.Index(fields=["user", "os_fingerprint"], name="device_user_osfp_idx"),
        ),
    ]
