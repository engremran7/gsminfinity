# apps/consent/apps.py
"""
Consent App Configuration
--------------------------
Initializes the Consent Management subsystem.
Ensures signal registration and avoids double import duplication.
"""

import logging
from django.apps import AppConfig

log = logging.getLogger(__name__)


class ConsentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.consent"
    label = "consent"
    verbose_name = "Consent Management"

    def ready(self):
        """
        App startup logic:
        ✅ Imports signals after Django app registry is ready
        ✅ Prevents double import issues under ASGI/WSGI reloads
        ✅ Provides safe logging for debugging startup issues
        """
        # Avoid running twice under autoreload (common in runserver)
        if getattr(self, "_consent_ready_ran", False):
            return
        self._consent_ready_ran = True

        try:
            import apps.consent.signals  # noqa: F401
            log.debug("Consent signals registered successfully.")
        except ImportError:
            log.info("No consent signals found (skipping registration).")
        except Exception as exc:
            log.warning(f"Error importing consent signals: {exc}")
