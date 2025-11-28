from __future__ import annotations

from typing import Optional

from apps.ads.models import AffiliateLink, AffiliateSource
from apps.site_settings.models import SiteSettings


def affiliate_enabled() -> bool:
    try:
        ss = SiteSettings.get_solo()
        return bool(getattr(ss, "affiliate_enabled", False))
    except Exception:
        return False


def resolve_link(name: str, source_name: str) -> Optional[str]:
    if not affiliate_enabled():
        return None
    source = AffiliateSource.objects.filter(name=source_name, is_enabled=True).first()
    if not source:
        return None
    link = AffiliateLink.objects.filter(source=source, name=name, is_enabled=True).first()
    return link.url if link else None
