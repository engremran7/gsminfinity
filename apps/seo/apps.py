from django.apps import AppConfig


class SeoConfig(AppConfig):
    name = "apps.seo"
    verbose_name = "SEO"

    def ready(self):
        try:
            import apps.seo.signals  # noqa: F401
        except Exception:
            return
