# Signal handlers for home page cache invalidation
"""
Listens to content updates and invalidates relevant widget caches
Ensures homepage always shows fresh data without manual cache clearing
"""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# === FIRMWARE SIGNALS ===


@receiver(post_save, sender="firmwares.OfficialFirmware")
@receiver(post_save, sender="firmwares.EngineeringFirmware")
@receiver(post_save, sender="firmwares.ReadbackFirmware")
@receiver(post_save, sender="firmwares.ModifiedFirmware")
@receiver(post_save, sender="firmwares.OtherFirmware")
def invalidate_firmware_caches(sender, instance, created, **kwargs):
    """Invalidate firmware widget caches when new firmware added"""
    if created:
        from .widgets import HomePageWidgetService

        HomePageWidgetService.invalidate_caches(["latest_firmwares"])
        logger.debug(f"Invalidated latest firmwares cache: {sender.__name__} created")


@receiver(post_save, sender="firmwares.FirmwareView")
@receiver(post_save, sender="firmwares.FirmwareDownloadAttempt")
def invalidate_trending_firmware_cache(sender, instance, created, **kwargs):
    """Invalidate trending cache when views/downloads change"""
    if created:
        # Don't invalidate on every view (too expensive), rely on periodic aggregation
        # Cache will naturally expire in 5 minutes
        pass


@receiver(post_save, sender="firmwares.FirmwareRequest")
def invalidate_requested_firmware_cache(sender, instance, **kwargs):
    """Invalidate most requested cache when request created/updated"""
    from .widgets import HomePageWidgetService

    HomePageWidgetService.invalidate_caches(["most_requested"])
    logger.debug("Invalidated most requested firmwares cache")


@receiver(post_delete, sender="firmwares.FirmwareRequest")
def invalidate_requested_on_delete(sender, instance, **kwargs):
    """Invalidate when request deleted (e.g., fulfilled)"""
    from .widgets import HomePageWidgetService

    HomePageWidgetService.invalidate_caches(["most_requested"])


# === BLOG SIGNALS ===


@receiver(post_save, sender="blog.Post")
def invalidate_blog_caches(sender, instance, **kwargs):
    """Invalidate blog widget caches when post published"""
    # Only invalidate if post is published
    if hasattr(instance, "status") and instance.status == "published":
        from .widgets import HomePageWidgetService

        HomePageWidgetService.invalidate_caches(["latest_blogs"])
        logger.debug("Invalidated latest blogs cache")


@receiver(post_delete, sender="blog.Post")
def invalidate_blogs_on_delete(sender, instance, **kwargs):
    """Invalidate when blog post deleted"""
    from .widgets import HomePageWidgetService

    HomePageWidgetService.invalidate_caches(["latest_blogs", "trending_blogs"])


# === CORE SIGNAL LISTENERS (from apps.core.signals) ===

# If you have custom signals defined in apps.core.signals, listen to them
try:
    from apps.core.signals import (
        firmware_download_ready,
        firmware_uploaded,
    )

    @receiver(firmware_uploaded)
    def on_firmware_uploaded_signal(sender, storage_location, firmware, **kwargs):
        """Invalidate when firmware uploaded via storage app"""
        from .widgets import HomePageWidgetService

        HomePageWidgetService.invalidate_caches(["latest_firmwares"])
        logger.debug("Invalidated caches via firmware_uploaded signal")

    @receiver(firmware_download_ready)
    def on_firmware_download_signal(sender, session, **kwargs):
        """Track download completions for trending calculation"""
        # This is tracked via FirmwareDownloadAttempt model
        pass

except ImportError:
    logger.warning("Core signals not available - some cache invalidation may not work")
