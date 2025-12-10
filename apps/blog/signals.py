
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.utils import feature_flags
from apps.seo.auto import apply_post_seo
from apps.seo.services.internal_linking.engine import refresh_linkable_entity
from apps.users.services.notifications import broadcast_notification, notifications_enabled
from apps.users.models import CustomUser
from .models import Post, PostStatus
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _sync_tag_usage(post: Post) -> None:
    try:
        tags = post.tags.all()
        for tag in tags:
            count = tag.posts.filter(status=PostStatus.PUBLISHED).count()
            if tag.usage_count != count:
                tag.usage_count = count
                tag.save(update_fields=["usage_count"])
    except Exception:
        logger.debug("Tag usage sync failed for post %s", post.pk)


def _ensure_post_seo(post: Post) -> None:
    if not feature_flags.seo_enabled():
        return
    try:
        apply_post_seo(post)
        refresh_linkable_entity(
            post,
            title=post.title,
            url=post.get_absolute_url(),
            keywords=",".join(post.tags.values_list("name", flat=True)),
        )
    except Exception:
        logger.debug("SEO sync failed for post %s", post.pk, exc_info=True)


@receiver(post_save, sender=Post)
def post_after_save(sender, instance: Post, **kwargs):
    _sync_tag_usage(instance)
    _ensure_post_seo(instance)

    # Notify users when a new post is published (only on initial create)
    created = kwargs.get("created", False)
    if created and instance.status == PostStatus.PUBLISHED and instance.is_live and notifications_enabled():
        try:
            recipients = CustomUser.objects.filter(is_active=True)
            broadcast_notification(
                recipients,
                title="New blog post",
                message=f"{instance.title} is now live.",
                level="info",
                url=instance.get_absolute_url(),
                channel="web",
                action_type="post",
                icon="file-text",
            )
        except Exception:
            logger.debug("post_after_save notification failed for post %s", instance.pk, exc_info=True)

    # Ping search engines on publish
    if created and instance.status == PostStatus.PUBLISHED and instance.is_live:
        try:
            sitemap_url = getattr(settings, "SITE_URL", "").rstrip("/") + "/sitemap.xml"
            if sitemap_url.startswith("http"):
                for ping in [
                    f"https://www.google.com/ping?sitemap={sitemap_url}",
                    f"https://www.bing.com/ping?sitemap={sitemap_url}",
                ]:
                    try:
                        requests.get(ping, timeout=3)
                    except Exception:
                        continue
        except Exception:
            logger.debug("post_after_save ping failed for post %s", instance.pk, exc_info=True)


