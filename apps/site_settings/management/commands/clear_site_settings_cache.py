from django.core.management.base import BaseCommand
from apps.site_settings.signals import clear_site_settings_cache

class Command(BaseCommand):
    help = "Clear site settings caches (singleton and per-site keys)."

    def handle(self, *args, **options):
        clear_site_settings_cache()
        self.stdout.write(self.style.SUCCESS("Site settings caches cleared."))