
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.blog.models import Post, PostStatus
from . import services
from .tasks import enqueue_pending_for_account
from .models import SocialAccount

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def on_post_publish(sender, instance: Post, **kwargs):
    if instance.status != PostStatus.PUBLISHED:
        return
    try:
        services.fanout_post_publish(instance)
    except Exception:
        logger.exception("Failed to enqueue distribution plan for post %s", instance.pk)


@receiver(post_save, sender=SocialAccount)
def on_social_account_activate(sender, instance: SocialAccount, **kwargs):
    if not instance.is_active:
        return
    try:
        count = enqueue_pending_for_account(instance)
        if count:
            logger.info("distribution.jobs.enqueued", extra={"channel": instance.channel, "count": count})
    except Exception:
        logger.exception("Failed to enqueue jobs for channel %s", instance.channel)


