from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from apps.ads.models import AdEvent, AdPlacement, AdCreative, Campaign
from apps.core.utils import feature_flags
from apps.core.utils.logging import log_event

logger = logging.getLogger(__name__)


def record_event(
    event_type: str,
    placement: Optional[AdPlacement] = None,
    creative: Optional[AdCreative] = None,
    campaign: Optional[Campaign] = None,
    user=None,
    request_meta: Optional[Dict[str, Any]] = None,
):
    if not feature_flags.ads_enabled():
        return

    try:
        payload = {
            "event_type": event_type,
            "placement": placement,
            "creative": creative,
            "campaign": campaign,
            "user": user,
            "request_meta": request_meta or {},
            "page_url": (request_meta or {}).get("page_url", ""),
            "referrer_url": (request_meta or {}).get("referrer", ""),
            "user_agent": (request_meta or {}).get("user_agent", ""),
            "session_id": (request_meta or {}).get("session_id", ""),
            "site_domain": (request_meta or {}).get("site", ""),
        }
        AdEvent.objects.create(**payload)
        log_event(
            logger,
            "info",
            "ads.event.recorded",
            event_type=event_type,
            placement=getattr(placement, "slug", None),
            creative=getattr(creative, "id", None),
            campaign=getattr(campaign, "id", None),
        )
    except Exception:
        logger.warning("record_event failed", exc_info=True)
