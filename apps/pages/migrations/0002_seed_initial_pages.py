from django.db import migrations
from django.utils import timezone


def seed_pages(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    # Note: "home" page is NOT seeded because homepage is handled by
    # home_landing view at root URL, not by pages app CMS
    defaults = [
        ("privacy", "Privacy Policy", "Privacy policy content goes here."),
        ("terms", "Terms of Service", "Terms of service content goes here."),
        ("cookies", "Cookies Policy", "Cookies policy content goes here."),
    ]
    now = timezone.now()
    for slug, title, content in defaults:
        Page.objects.update_or_create(
            slug=slug,
            defaults={
                "title": title,
                "content": content,
                "status": "published",
                "access_level": "public",
                "include_in_sitemap": True,
                "publish_at": now,
            },
        )


def remove_seed(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    Page.objects.filter(slug__in=["privacy", "terms", "cookies"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_pages, reverse_code=remove_seed),
    ]
