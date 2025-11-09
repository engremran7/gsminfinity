"""
apps.users.apps
----------------
Application configuration for GSMInfinity's Users module.

Responsibilities:
- Auto-register user signals (login, signup, profile creation)
- Integrate cleanly with django-allauth adapters/forms
- Safe import guards to avoid ORM or AppRegistry errors during startup
"""

from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules
import logging


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"
    verbose_name = "User Management"

    def ready(self):
        """
        App initialization hook called once Django is fully loaded.

        Tasks performed:
        - Import user signal handlers safely
        - Discover additional 'signals' submodules across apps
        - Prevent ImportErrors from halting migrations or shell startup
        """
        logger = logging.getLogger(__name__)

        # ---------------------------------------------------------------
        # 1️⃣ Import this app's signals safely
        # ---------------------------------------------------------------
        try:
            import apps.users.signals  # noqa: F401
            logger.debug("apps.users.signals successfully imported.")
        except ImportError as exc:
            logger.warning(f"UsersConfig: unable to import signals ({exc}). Skipping.")

        # ---------------------------------------------------------------
        # 2️⃣ Autodiscover cross-app signal modules (optional)
        # ---------------------------------------------------------------
        try:
            autodiscover_modules("signals")
            logger.debug("UsersConfig: autodiscovered 'signals' modules.")
        except Exception as exc:
            logger.debug(f"UsersConfig: autodiscover_modules failed ({exc}).")

        # ---------------------------------------------------------------
        # 3️⃣ Future extension hook (startup tasks, audits, etc.)
        # ---------------------------------------------------------------
        # Example: pre-warm device fingerprint cache, schedule syncs, etc.
        # Keep this lightweight — ready() runs on every process start.
        return
