from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from apps.core.utils import feature_flags
from apps.seo.models import SEOModel, Metadata
from apps.seo.services.internal_linking.engine import refresh_linkable_entity
from .models import Post, PostStatus

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
        ct = ContentType.objects.get_for_model(Post)
        seo_obj, _ = SEOModel.objects.get_or_create(content_type=ct, object_id=post.pk)
        meta, _ = Metadata.objects.get_or_create(seo=seo_obj)
        if not meta.meta_title:
            meta.meta_title = post.seo_title or post.title
        if not meta.meta_description:
            meta.meta_description = post.seo_description or post.summary[:320]
        meta.save()
        refresh_linkable_entity(
            post,
            title=post.title,
            url=post.get_absolute_url(),
            keywords=",".join(post.tags.values_list("name", flat=True)),
        )
    except Exception:
        logger.debug("SEO sync failed for post %s", post.pk)


@receiver(post_save, sender=Post)
def post_after_save(sender, instance: Post, **kwargs):
    _sync_tag_usage(instance)
    _ensure_post_seo(instance)
