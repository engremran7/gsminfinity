from __future__ import annotations

import random
from typing import Iterable, Optional

from apps.ads.models import PlacementAssignment, AdCreative, AdPlacement
from apps.site_settings.models import SiteSettings
from apps.core.utils import feature_flags
from apps.core.utils.logging import log_event
import logging

logger = logging.getLogger(__name__)


def _aggressiveness_multiplier() -> int:
    try:
        level = SiteSettings.get_solo().ad_aggressiveness_level
    except Exception:
        level = "balanced"
    if level == "minimal":
        return 1
    if level == "aggressive":
        return 3
    return 2


def choose_creative(placement: AdPlacement) -> Optional[AdCreative]:
    """
    Weighted random selection among enabled assignments for a placement.
    Aggressiveness controls how heavily weights are emphasized.
    """
    if not feature_flags.ads_enabled():
        return None
    qs: Iterable[PlacementAssignment] = placement.assignments.filter(
        is_enabled=True, is_active=True, creative__is_enabled=True, creative__is_active=True
    ).select_related("creative", "creative__campaign")
    pool = []
    mult = _aggressiveness_multiplier()
    for a in qs:
        creative = a.creative
        if creative.campaign and not creative.campaign.is_live() and not creative.campaign.locked:
            continue
        weight = max(1, a.weight * mult)
        pool.extend([creative] * weight)
    if not pool:
        log_event(logger, "warning", "ads.rotation.no_pool", placement=placement.slug)
        return None
    choice = random.choice(pool)
    log_event(
        logger,
        "info",
        "ads.rotation.selected",
        placement=placement.slug,
        creative=choice.id,
        campaign=getattr(choice.campaign, "id", None),
    )
    return choice
