from django.apps import AppConfig


class FirmwaresConfig(AppConfig):
    """
    Firmware management app for multi-brand GSM device firmware distribution
    Features: Tracking, analytics, trending, request management
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.firmwares"
    verbose_name = "Firmwares"
    
    def ready(self):
        """Register signal handlers when app is ready"""
        try:
            # Import signal handlers for tracking, storage integration, and cache invalidation
            import apps.firmwares.signal_handlers
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to register firmwares signal handlers: {e}")
