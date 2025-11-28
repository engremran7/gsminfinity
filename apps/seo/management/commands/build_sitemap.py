from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.sites.models import Site

from apps.seo.models import SitemapEntry
from apps.blog.models import Post, PostStatus


class Command(BaseCommand):
    help = "Builds sitemap entries from published blog posts."

    def handle(self, *args, **options):
        now = timezone.now()
        domain = getattr(Site.objects.get_current(), "domain", "")
        total = 0
        posts = Post.objects.filter(status=PostStatus.PUBLISHED)
        for p in posts:
            url = p.get_absolute_url() if hasattr(p, "get_absolute_url") else ""
            if domain and url.startswith("/"):
                url = f"https://{domain}{url}"
            if not url:
                continue
            SitemapEntry.objects.update_or_create(
                url=url,
                defaults={
                    "lastmod": p.updated_at or now,
                    "changefreq": "weekly",
                    "priority": 0.7,
                    "is_active": True,
                },
            )
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Sitemap build complete. Entries: {total}"))
