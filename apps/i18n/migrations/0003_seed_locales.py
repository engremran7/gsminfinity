from django.db import migrations

def seed_locales(apps, schema_editor):
    Locale = apps.get_model('i18n', 'Locale')
    defaults = [
        ('en', 'English', 'ltr'),
        ('ar', 'Arabic', 'rtl'),
        ('ur', 'Urdu', 'rtl'),
    ]
    for code, name, direction in defaults:
        Locale.objects.update_or_create(code=code, defaults={'name': name, 'direction': direction})


def unseed_locales(apps, schema_editor):
    Locale = apps.get_model('i18n', 'Locale')
    Locale.objects.filter(code__in=['en', 'ar', 'ur']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('i18n', '0002_rename_i18n_manifest_app_idx_i18n_appman_app_id_d95a76_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_locales, unseed_locales),
    ]
