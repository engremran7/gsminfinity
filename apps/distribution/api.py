
from __future__ import annotations

from typing import Any, Dict
from django.http import JsonResponse, HttpRequest, Http404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST

# Placeholder for future DistributionSettings if needed


def get_settings() -> Dict[str, Any]:
    """
    Stub settings for distribution module; extend with real toggles as needed.
    Default to disabled in production.
    """
    return {"distribution_enabled": False}


@staff_member_required
@require_POST
def api_send_test(request: HttpRequest, slug: str):
    """
    Minimal placeholder view used for internal smoke checks. Staff-only to avoid exposing test endpoints publicly.
    """
    if not request.user.is_staff:
        raise Http404()
    return JsonResponse({"ok": True, "slug": slug})


__all__ = ["get_settings", "api_send_test"]


