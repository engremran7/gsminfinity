from django.apps import AppConfig


class PagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pages"
    verbose_name = "Pages"

    def ready(self):
        # Register the static sitemap to ensure core routes appear even if not backed by Page rows.
        try:
            from apps.pages.sitemap_registry import register_sitemap
            from apps.pages.sitemaps import StaticViewsSitemap

            register_sitemap("static", StaticViewsSitemap)
        except Exception:
            pass

        # Register signal handlers for homepage widget cache invalidation
        try:
            pass
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to register pages signal handlers: {e}"
            )
