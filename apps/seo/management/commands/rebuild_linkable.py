from __future__ import annotations

from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType

from apps.blog.models import Post
from apps.seo.services.internal_linking.engine import refresh_linkable_entity


class Command(BaseCommand):
    help = "Rebuild LinkableEntity registry from blog posts (extend for other models)."

    def handle(self, *args, **options):
        count = 0
        for post in Post.objects.all():
            url = post.get_absolute_url() if hasattr(post, "get_absolute_url") else ""
            refresh_linkable_entity(post, title=post.title, url=url, keywords=post.summary or "")
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Linkable entities refreshed: {count}"))
