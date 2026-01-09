
from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
    verbose_name = "Core"

    def ready(self):
        """
        Core app initialization:
        - Validate critical security keys (FERNET_KEY, MFA_ENCRYPTION_KEY)
        - Safely clear the django.contrib.sites cache after registry load
        - Autodiscover signals or other startup modules
        """
        # Validate critical encryption keys at startup
        self._validate_encryption_keys()
        
        try:
            from django.contrib.sites.models import Site

            Site.objects.clear_cache()
        except Exception:
            pass

        # Auto-discover signals.py in submodules
        autodiscover_modules("signals")
    
    def _validate_encryption_keys(self) -> None:
        """
        Validate FERNET_KEY and MFA_ENCRYPTION_KEY at startup.
        
        Raises:
            ImproperlyConfigured: If keys are missing or invalid in production.
        """
        import base64
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured
        
        is_production = not settings.DEBUG
        
        # Validate FERNET_KEY (required for firmware password encryption)
        fernet_key = getattr(settings, "FERNET_KEY", None)
        if not fernet_key:
            if is_production:
                raise ImproperlyConfigured(
                    "FERNET_KEY must be set in production. Generate with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        else:
            try:
                raw = base64.urlsafe_b64decode(fernet_key)
                if len(raw) < 32:
                    raise ImproperlyConfigured("FERNET_KEY must decode to at least 32 bytes")
            except Exception as exc:
                raise ImproperlyConfigured(
                    f"FERNET_KEY is invalid (must be urlsafe base64 encoded 32-byte key): {exc}"
                ) from exc
        
        # Validate MFA_ENCRYPTION_KEY (required for MFA secret encryption)
        mfa_key = getattr(settings, "MFA_ENCRYPTION_KEY", None)
        if not mfa_key:
            if is_production:
                raise ImproperlyConfigured(
                    "MFA_ENCRYPTION_KEY must be set in production. "
                    "Use a strong random key separate from SECRET_KEY to allow safe key rotation."
                )
        elif len(mfa_key) < 32:
            if is_production:
                raise ImproperlyConfigured(
                    "MFA_ENCRYPTION_KEY must be at least 32 characters long for security."
                )

