from __future__ import annotations

from django.db import migrations, models


def backfill_device_key_id(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    for d in Device.objects.all():
        if not getattr(d, "device_key_id", None):
            d.device_key_id = getattr(d, "hardware_uuid", "") or str(d.id)
            d.key_algorithm = "ES256"
            d.save(update_fields=["device_key_id", "key_algorithm"])


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0009_deduplicate_devices"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="device_key_id",
            field=models.CharField(db_index=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="device",
            name="key_algorithm",
            field=models.CharField(choices=[("ES256", "ES256"), ("Ed25519", "Ed25519")], default="ES256", max_length=20),
        ),
        migrations.AddField(
            model_name="device",
            name="public_key",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterUniqueTogether(
            name="device",
            unique_together={("user", "device_key_id")},
        ),
        migrations.RunPython(backfill_device_key_id, migrations.RunPython.noop),
    ]
