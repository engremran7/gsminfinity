
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.blog.models import Post, PostStatus
from . import services

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def on_post_publish(sender, instance: Post, **kwargs):
    if instance.status != PostStatus.PUBLISHED:
        return
    try:
        services.fanout_post_publish(instance)
    except Exception:
        logger.exception("Failed to enqueue distribution plan for post %s", instance.pk)


