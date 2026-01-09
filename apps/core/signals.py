
"""
apps.core.signals
-----------------
Seeds singleton settings so the admin never asks to create configs.
This runs post-migrate and is defensive: if an app is missing or migrations
are not applied yet, it quietly skips.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from django.apps import apps as django_apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


SINGLETON_MODELS: Iterable[str] = (
    "apps.core.models.AppRegistry",
    "apps.site_settings.models.SiteSettings",
    "apps.devices.models.DeviceConfig",
    "apps.ads.models.AdsSettings",
    "apps.seo.models.SEOSettings",
    "apps.tags.models.TagsSettings",
    "apps.comments.models.CommentSettings",
    "apps.blog.models.BlogSettings",
    "apps.distribution.models.DistributionSettings",
    "apps.users.models.UsersSettings",
    "apps.ai.models.AISettings",
)

DEFAULT_APP_POLICY = {
    "name": "default",
}


def _is_installed(model_path: str) -> bool:
    """
    Return True if the Django app for the model_path is installed.
    model_path example: 'apps.seo.models.SEOSettings'
    """
    try:
        app_label = model_path.split(".")[1]
    except Exception:
        return False
    return django_apps.is_installed(f"apps.{app_label}")


def _ensure_singleton(model_path: str) -> None:
    """
    Ensure a singleton model has one row. Best-effort, never raises.
    """
    if not _is_installed(model_path):
        return
    try:
        model = import_string(model_path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Singleton seed skipped (%s): %s", model_path, exc)
        return

    try:
        if hasattr(model, "get_solo"):
            model.get_solo()
        elif hasattr(model, "objects"):
            model.objects.get_or_create(pk=1)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Singleton seed failed (%s): %s", model_path, exc)


@receiver(post_migrate)
def seed_singletons(sender, **kwargs):  # pragma: no cover - signal hook
    """
    After migrations, ensure all singleton settings exist so admin shows
    “edit” instead of “create configuration”.
    """
    for model_path in SINGLETON_MODELS:
        _ensure_singleton(model_path)

    # Seed a default AppPolicy if devices app is installed
    if _is_installed("apps.devices.models.AppPolicy"):
        try:
            from apps.devices.models import AppPolicy

            AppPolicy.objects.get_or_create(name=DEFAULT_APP_POLICY["name"], defaults=DEFAULT_APP_POLICY)
        except Exception as exc:
            logger.debug("Default AppPolicy seed skipped: %s", exc)

# ============================================================================
# Cross-App Communication Signals
# ============================================================================
# These signals enable loose coupling between apps without circular dependencies.
# Apps emit signals instead of calling each other's code directly.

from django.dispatch import Signal

# Blog signals
blog_post_published = Signal()  # args: post, user
blog_post_updated = Signal()  # args: post, user
blog_post_deleted = Signal()  # args: post_id, user

# Comment signals
comment_created = Signal()  # args: comment, user
comment_approved = Signal()  # args: comment
comment_flagged = Signal()  # args: comment, reason

# User signals
user_registered = Signal()  # args: user, request
user_profile_updated = Signal()  # args: user
user_login_success = Signal()  # args: user, request

# SEO signals
seo_metadata_requested = Signal()  # args: content_object, force_regenerate
seo_sitemap_updated = Signal()  # args: sitemap_type

# Device signals
device_fingerprint_created = Signal()  # args: device, user
device_suspicious_activity = Signal()  # args: device, activity_type

# Content signals
content_viewed = Signal()  # args: content_object, user, request
content_shared = Signal()  # args: content_object, platform, user

# Notification signals
notification_send_requested = Signal()  # args: user_ids, title, message, notification_type

# Storage signals (firmware download/upload)
firmware_upload_requested = Signal()  # args: firmware_object, local_path, metadata
firmware_uploaded = Signal()  # args: firmware_object, storage_location
firmware_download_requested = Signal()  # args: firmware_object, user
firmware_download_ready = Signal()  # args: session, user, file_name, expires_at
storage_quota_exhausted = Signal()  # args: shared_drive, utilization_percent
storage_health_critical = Signal()  # args: shared_drive, issue
