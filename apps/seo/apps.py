
from django.apps import AppConfig


class SeoConfig(AppConfig):
    name = "apps.seo"
    verbose_name = "SEO"

    def ready(self):
        try:
            import apps.seo.signals  # noqa: F401
        except Exception:
            return

        # Register SEO sitemap entries into the shared registry
        try:
            from apps.pages.sitemap_registry import register_sitemap
            from .sitemaps import ActiveSeoEntriesSitemap

            register_sitemap("seo", ActiveSeoEntriesSitemap)
        except Exception:
            # Keep failure silent to avoid breaking startup when pages app is absent.
            return


