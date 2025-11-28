from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class SiteSettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.site_settings"  # full Python path
    label = "site_settings"  # short label
    verbose_name = "Site Settings"

    def ready(self):
        """
        Initialize site settings and related signals.

        - Loads signal hooks to sync database-based settings
        - Avoids circular imports during startup
        - Autodiscovers additional settings modules if needed
        """
        try:
            import apps.site_settings.signals  # noqa: F401
        except ImportError:
            pass

        autodiscover_modules("signals")