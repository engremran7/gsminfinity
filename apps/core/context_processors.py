# apps/site_settings/context_processors.py
from django.core.cache import cache
from apps.site_settings.models import SiteSettings


def global_settings(request):
    """
    Injects global site settings and dynamic configuration into all templates.

    Provides:
    - Branding metadata (site name, description, favicon)
    - Theme and color preferences
    - Localization and timezone info
    - Security & feature toggles
    - AI personalization preferences

    Uses caching for performance and fallbacks for uninitialized environments.
    """
    cache_key = "global_site_settings"
    settings_obj = cache.get(cache_key)

    if not settings_obj:
        try:
            settings_obj = SiteSettings.get_solo()
            cache.set(cache_key, settings_obj, timeout=300)
        except Exception:
            # Fallback dummy for environments where SiteSettings is not initialized
            class Dummy:
                site_name = "GSMInfinity"
                site_header = "GSM Admin"
                site_description = "Default site description"
                favicon = None
                theme_profile = "default"
                primary_color = "#0d6efd"
                secondary_color = "#6c757d"
                default_language = "en-us"
                timezone = "UTC"
                enable_localization = True
                maintenance_mode = False
                enable_signup = True
                enable_password_reset = True
                enable_notifications = True
                enable_ai_personalization = False
                ai_theme_mode = "adaptive"
                ai_model_version = "gpt-5.0"

            settings_obj = Dummy()

    # Safe attribute access for all template variables
    s = settings_obj
    return {
        # Branding
        "site_name": getattr(s, "site_name", "GSMInfinity"),
        "site_header": getattr(s, "site_header", ""),
        "site_description": getattr(s, "site_description", ""),
        "favicon": getattr(s, "favicon", None),

        # Theme
        "theme_profile": getattr(s, "theme_profile", "default"),
        "primary_color": getattr(s, "primary_color", "#0d6efd"),
        "secondary_color": getattr(s, "secondary_color", "#6c757d"),

        # Locale
        "default_language": getattr(s, "default_language", "en-us"),
        "timezone": getattr(s, "timezone", "UTC"),
        "enable_localization": getattr(s, "enable_localization", True),

        # Security & Features
        "maintenance_mode": getattr(s, "maintenance_mode", False),
        "enable_signup": getattr(s, "enable_signup", True),
        "enable_password_reset": getattr(s, "enable_password_reset", True),
        "enable_notifications": getattr(s, "enable_notifications", True),

        # AI personalization
        "enable_ai_personalization": getattr(s, "enable_ai_personalization", False),
        "ai_theme_mode": getattr(s, "ai_theme_mode", "adaptive"),
        "ai_model_version": getattr(s, "ai_model_version", "gpt-5.0"),
    }
