from __future__ import annotations

from django.db import migrations


def dedupe_devices(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    seen = set()
    to_delete = []
    qs = Device.objects.order_by("user_id", "-last_seen_at")
    for d in qs:
        key = (d.user_id, getattr(d, "hardware_uuid", "") or "")
        if key in seen:
            to_delete.append(d.pk)
        else:
            seen.add(key)
    if to_delete:
        Device.objects.filter(pk__in=to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0008_remove_device_device_user_machine_uuid_unique_and_more"),
    ]

    operations = [
        migrations.RunPython(dedupe_devices, migrations.RunPython.noop),
    ]
