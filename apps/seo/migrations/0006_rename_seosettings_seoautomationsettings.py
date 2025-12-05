from django.db import migrations


class Migration(migrations.Migration):
    """
    No-op: original intent was to rename SeoSettings to SeoAutomationSettings.
    The CreateModel in 0005 already uses the final name/table, so keep this
    migration in the chain without altering schema.
    """

    dependencies = [
        ("seo", "0005_seosettings"),
    ]

    operations = []
