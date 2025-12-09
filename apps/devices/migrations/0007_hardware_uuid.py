from __future__ import annotations

from django.db import migrations, models


def copy_machine_uuid_to_hardware(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    for d in Device.objects.all():
        if not getattr(d, "hardware_uuid", None):
            setattr(d, "hardware_uuid", getattr(d, "machine_uuid", "") or "")
            d.save(update_fields=["hardware_uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0006_userdevicequota"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="hardware_uuid",
            field=models.CharField(db_index=True, default="", max_length=128),
        ),
        migrations.RunPython(copy_machine_uuid_to_hardware, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="device",
            unique_together={("user", "hardware_uuid")},
        ),
        migrations.AddIndex(
            model_name="device",
            index=models.Index(fields=["user", "hardware_uuid"], name="device_user_hardware_idx"),
        ),
    ]
