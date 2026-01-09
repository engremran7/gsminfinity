from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

# NOTE: Cross-app imports are deferred to prevent circular dependencies
# Blog imports SEO, SEO cannot import Blog at module level

logger = logging.getLogger(__name__)


def connect_signals():
    """
    Connect SEO signals. Called from AppConfig.ready().
    Uses lazy imports to prevent circular dependencies.
    """
    from apps.blog.models import Post
    from apps.seo.services.internal_linking.engine import refresh_linkable_entity

    @receiver(post_save, sender=Post)
    def sync_linkable_for_post(sender, instance, **kwargs):
        """
        Keep LinkableEntity in sync for blog posts without altering links automatically.
        """
        try:
            url = (
                instance.get_absolute_url()
                if hasattr(instance, "get_absolute_url")
                else ""
            )
            refresh_linkable_entity(
                instance, title=instance.title, url=url, keywords=instance.summary or ""
            )
        except Exception:
            logger.debug(
                "Failed to sync linkable entity for post %s", instance.pk, exc_info=True
            )
