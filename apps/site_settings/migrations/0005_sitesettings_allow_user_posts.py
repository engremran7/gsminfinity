from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("site_settings", "0004_sitesettings_ad_aggressiveness_level_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="allow_user_blog_posts",
            field=models.BooleanField(
                default=False,
                help_text="When on, authenticated users (non-admin) can create blog posts.",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="allow_user_bounty_posts",
            field=models.BooleanField(
                default=False,
                help_text="When on, authenticated users can create bounty posts (tagged 'bounty').",
            ),
        ),
    ]
