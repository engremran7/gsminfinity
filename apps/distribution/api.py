
from __future__ import annotations

from typing import Any, Dict
from django.http import JsonResponse, HttpRequest

# Placeholder for future DistributionSettings if needed


def get_settings() -> Dict[str, Any]:
    """
    Stub settings for distribution module; extend with real toggles as needed.
    """
    return {"distribution_enabled": True}


def api_send_test(request: HttpRequest, slug: str):
    """
    Minimal placeholder view to satisfy URL import; replace with real implementation.
    """
    return JsonResponse({"ok": True, "slug": slug})


__all__ = ["get_settings", "api_send_test"]


