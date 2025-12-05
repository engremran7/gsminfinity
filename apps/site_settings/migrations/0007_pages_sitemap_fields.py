from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0006_remove_sitesettings_ad_aggressiveness_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="pages_enabled",
            field=models.BooleanField(default=True, help_text="Enable dynamic pages app for public pages."),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="sitemap_enabled",
            field=models.BooleanField(default=True, help_text="Expose sitemap.xml for published pages."),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="sitemap_index_enabled",
            field=models.BooleanField(default=True, help_text="Expose sitemap_index.xml for published pages."),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="sitemap_page_size",
            field=models.PositiveIntegerField(default=2000, help_text="Max URLs per sitemap chunk."),
        ),
    ]
