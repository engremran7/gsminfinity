from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.utils import feature_flags

from .models import SiteSettings, VerificationFile, VerificationMetaTag


def clear_site_settings_cache():
    """
    Invalidate all site settings caches.

    - Per-site caches use 'site_settings_<site_id>'.
    - Called whenever SiteSettings or related verification
      resources are saved or deleted.
    """
    try:
        for site_id in Site.objects.values_list("id", flat=True):
            cache.delete(f"site_settings_{site_id}")
    except Exception:
        # During migrations or initial setup, Site table may not exist yet.
        pass


@receiver(post_save, sender=SiteSettings)
@receiver(post_delete, sender=SiteSettings)
@receiver(post_save, sender=VerificationMetaTag)
@receiver(post_delete, sender=VerificationMetaTag)
@receiver(post_save, sender=VerificationFile)
@receiver(post_delete, sender=VerificationFile)
def invalidate_site_settings_cache(sender, **kwargs):
    """
    Signal handler to clear cached site settings whenever relevant models change.
    """
    clear_site_settings_cache()
    feature_flags.reset_cache()
