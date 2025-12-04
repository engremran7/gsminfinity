
"""
apps.core.signals
-----------------
Seeds singleton settings so the admin never asks to create configs.
This runs post-migrate and is defensive: if an app is missing or migrations
are not applied yet, it quietly skips.
"""

from __future__ import annotations

import logging
from typing import Iterable

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
    "apps.i18n_themes.models.LanguageProfile",
    # users referral system is disabled; ensure a baseline UsersSettings row exists but leave referral optional
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

    # Seed baseline language profile + locales for i18n_themes
    if _is_installed("apps.i18n_themes.models.Locale"):
        try:
            from apps.i18n_themes.models import LanguageProfile, Locale

            # Baseline locales
            for code, name, direction in (
                ("en", "English", "ltr"),
                ("ur", "Urdu", "rtl"),
                ("ar", "Arabic", "rtl"),
            ):
                Locale.objects.get_or_create(
                    code=code,
                    defaults={"name": name, "direction": direction, "enabled_global": True},
                )

            # Baseline language profile for core app
            LanguageProfile.objects.get_or_create(
                app_id="core",
                site_id=None,
                defaults={"default_locale": "en", "supported_locales": ["en", "ur"], "fallback_locale": "en"},
            )
        except Exception as exc:
            logger.debug("Default i18n locales/profile seed skipped: %s", exc)


