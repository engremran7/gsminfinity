
from __future__ import annotations

import logging

from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

# NOTE: Cross-app imports are deferred to prevent circular dependencies
# Blog is imported lazily to avoid circular import with distribution

logger = logging.getLogger(__name__)


def connect_signals():
    """
    Connect distribution signals. Called from AppConfig.ready().
    Uses lazy imports to prevent circular dependencies.
    Checks if blog app is installed for modularity.
    """
    from . import services
    from .tasks import enqueue_pending_for_account

    # Only connect blog signals if blog app is installed (modularity)
    if apps.is_installed('apps.blog'):
        try:
            from apps.blog.models import Post, PostStatus

            @receiver(post_save, sender=Post)
            def on_post_publish(sender, instance, **kwargs):
                if instance.status != PostStatus.PUBLISHED:
                    return
                try:
                    services.fanout_post_publish(instance)
                except Exception:
                    logger.exception("Failed to enqueue distribution plan for post %s", instance.pk)
        except Exception as e:
            logger.debug(f"Blog integration not available: {e}")

        try:
            count = enqueue_pending_for_account(instance)
            if count:
                logger.info("distribution.jobs.enqueued", extra={"channel": instance.channel, "count": count})
        except Exception:
            logger.exception("Failed to enqueue jobs for channel %s", instance.channel)


