from __future__ import annotations

from django.db import migrations


def dedupe_os_fingerprint(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    seen = set()
    to_delete = []
    qs = Device.objects.order_by("user_id", "-last_seen_at")
    for d in qs:
        key = (d.user_id, getattr(d, "os_fingerprint", "") or "")
        if key in seen:
            to_delete.append(d.pk)
            continue
        seen.add(key)
        try:
            # Keep legacy hardware_uuid aligned for backward compatibility
            if not getattr(d, "hardware_uuid", "") and getattr(d, "os_fingerprint", ""):
                d.hardware_uuid = d.os_fingerprint
                d.save(update_fields=["hardware_uuid"])
        except Exception:
            continue
    if to_delete:
        Device.objects.filter(pk__in=to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0012_remove_device_device_user_hardware_uuid_unique_and_more"),
    ]

    operations = [
        migrations.RunPython(dedupe_os_fingerprint, migrations.RunPython.noop),
    ]
