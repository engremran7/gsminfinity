
from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.blog"
    verbose_name = "Blog"

    def ready(self):
        from . import signals  # noqa: F401

        # Register blog sitemap with the central registry (soft-fail to keep app modular)
        try:
            from apps.pages.sitemap_registry import register_sitemap
            from .sitemaps import PublishedBlogPostsSitemap

            register_sitemap("blog", PublishedBlogPostsSitemap)
        except Exception:
            # If pages app or registry isn't ready, skip silently to avoid import-time failures.
            return


