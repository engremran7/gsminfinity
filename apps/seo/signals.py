from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from apps.blog.models import Post
from apps.seo.services.internal_linking.engine import refresh_linkable_entity


@receiver(post_save, sender=Post)
def sync_linkable_for_post(sender, instance: Post, **kwargs):
    """
    Keep LinkableEntity in sync for blog posts without altering links automatically.
    """
    try:
        url = instance.get_absolute_url() if hasattr(instance, "get_absolute_url") else ""
        refresh_linkable_entity(instance, title=instance.title, url=url, keywords=instance.summary or "")
    except Exception:
        return
