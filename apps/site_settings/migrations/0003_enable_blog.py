from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0002_enable_tenants"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="enable_blog",
            field=models.BooleanField(
                default=True,
                help_text="Enable public blog views.",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="enable_blog_comments",
            field=models.BooleanField(
                default=True,
                help_text="Enable comments on blog posts.",
            ),
        ),
    ]
