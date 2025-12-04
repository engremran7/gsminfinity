
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AdRequest:
    placement_code: str
    page_url: str
    referrer: str = ""
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    consent_ads: bool = False
    device: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CreativeSelection:
    creative_id: int
    campaign_id: Optional[int]
    weight: int
    reason: str = ""


@dataclass
class AdResponse:
    placement_code: str
    creatives: List[CreativeSelection]
    tracking: Dict[str, Any] = field(default_factory=dict)
    fallback: bool = False


