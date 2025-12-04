
from __future__ import annotations

from django.apps import AppConfig


class DistributionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.distribution"
    verbose_name = "Distribution"

    def ready(self) -> None:
        # Import signal handlers to connect blog publish fanout.
        from . import signals  # noqa: F401


