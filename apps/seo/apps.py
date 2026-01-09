from django.apps import AppConfig


class SeoConfig(AppConfig):
    name = "apps.seo"
    verbose_name = "SEO"

    def ready(self):
        # Connect signals with deferred imports to prevent circular dependencies
        try:
            from . import signals

            signals.connect_signals()
        except Exception:
            pass

        # Register signal handlers for cross-app communication
        try:
            from . import signal_handlers  # noqa: F401
        except Exception:
            pass

        # Register SEO sitemap entries into the shared registry
        try:
            from apps.pages.sitemap_registry import register_sitemap

            from .sitemaps import ActiveSeoEntriesSitemap

            register_sitemap("seo", ActiveSeoEntriesSitemap)
        except Exception:
            # Keep failure silent to avoid breaking startup when pages app is absent.
            return
