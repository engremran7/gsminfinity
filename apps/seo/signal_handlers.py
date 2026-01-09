"""
Signal handlers for SEO app
Responds to content signals without creating circular dependencies.
"""
import logging

from django.dispatch import receiver

from apps.core.signals import (
    blog_post_published,
    blog_post_updated,
    seo_metadata_requested,
    seo_sitemap_updated,
)

logger = logging.getLogger(__name__)


@receiver(blog_post_published)
def generate_seo_on_publish(sender, post, user, **kwargs):
    """Automatically generate SEO metadata when blog post is published"""
    try:
        from django.contrib.contenttypes.models import ContentType

        from apps.seo.models import SEOModel

        content_type = ContentType.objects.get_for_model(post)
        seo, created = SEOModel.objects.get_or_create(
            content_type=content_type,
            object_id=post.pk
        )

        if created or not hasattr(seo, 'metadata'):
            # Trigger SEO generation
            seo_metadata_requested.send(
                sender=sender,
                content_object=post,
                force_regenerate=False
            )
            logger.info(f"SEO metadata generation triggered for post: {post.pk}")

        # Trigger sitemap rebuild for blog content
        seo_sitemap_updated.send(sender=sender, sitemap_type='blog')

    except Exception as exc:
        logger.error(f"Failed to generate SEO for post {post.pk}: {exc}")


@receiver(blog_post_updated)
def update_seo_on_change(sender, post, user, **kwargs):
    """Update SEO metadata when blog post content changes"""
    try:
        from django.contrib.contenttypes.models import ContentType

        from apps.seo.models import SEOModel

        content_type = ContentType.objects.get_for_model(post)
        seo = SEOModel.objects.filter(
            content_type=content_type,
            object_id=post.pk
        ).first()

        if seo and hasattr(seo, 'metadata'):
            # Trigger regeneration if content hash changed
            seo_metadata_requested.send(
                sender=sender,
                content_object=post,
                force_regenerate=True
            )
            logger.info(f"SEO metadata update triggered for post: {post.pk}")
    except Exception as exc:
        logger.error(f"Failed to update SEO for post {post.pk}: {exc}")


@receiver(seo_sitemap_updated)
def rebuild_sitemap_cache(sender, sitemap_type, **kwargs):
    """Rebuild sitemap cache when content changes"""
    from django.core.cache import cache

    cache.delete(f'sitemap_{sitemap_type}')
    cache.delete('sitemap_index')
    logger.info(f"Cleared sitemap cache for type: {sitemap_type}")

    # Schedule async sitemap rebuild
    try:
        from apps.seo.tasks import build_sitemap_async
        build_sitemap_async.delay(sitemap_type=sitemap_type, notify=False)
        logger.info(f"Scheduled async sitemap rebuild for: {sitemap_type}")
    except Exception as e:
        logger.debug(f"Async sitemap rebuild skipped: {e}")


# -----------------------------------------------------------------------------
# Firmware SEO Integration
# -----------------------------------------------------------------------------
try:
    from apps.core.signals import firmware_uploaded

    @receiver(firmware_uploaded)
    def generate_seo_for_firmware(sender, firmware, **kwargs):
        """
        Generate SEO metadata and update sitemap when firmware is uploaded.
        This ensures firmware pages get proper SEO treatment.
        """
        try:
            # Trigger sitemap rebuild for firmware content
            seo_sitemap_updated.send(sender=sender, sitemap_type='firmwares')
            logger.info(f"SEO sitemap update triggered for firmware: {firmware.pk}")
        except Exception as exc:
            logger.error(f"Failed to trigger SEO for firmware {firmware.pk}: {exc}")

except ImportError:
    # firmware_uploaded signal not available
    pass
