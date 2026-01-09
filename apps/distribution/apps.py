from __future__ import annotations

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class DistributionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.distribution"
    verbose_name = "Distribution"

    def ready(self) -> None:
        # Connect signals with deferred imports to prevent circular dependencies
        # Wrapped in try/except for modularity - distribution app can work standalone
        try:
            from . import signals

            signals.connect_signals()
        except Exception as e:
            logger.debug(f"Distribution signals not connected: {e}")
