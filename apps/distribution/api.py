from __future__ import annotations

from typing import Any

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, JsonResponse
from django.views.decorators.http import require_POST

from apps.distribution.models import DistributionSettings


def get_settings() -> dict[str, Any]:
    """
    Resolve distribution settings from the singleton model with safe defaults.
    """
    try:
        cfg = DistributionSettings.get_solo()
        return {
            "distribution_enabled": cfg.distribution_enabled,
            "auto_fanout_on_publish": cfg.auto_fanout_on_publish,
            "default_channels": cfg.default_channels,
            "max_retries": cfg.max_retries,
            "retry_backoff_seconds": cfg.retry_backoff_seconds,
            "allow_indexing_jobs": cfg.allow_indexing_jobs,
        }
    except Exception:
        return {
            "distribution_enabled": False,
            "auto_fanout_on_publish": False,
            "default_channels": [],
            "max_retries": 3,
            "retry_backoff_seconds": 1800,
            "allow_indexing_jobs": False,
        }


@staff_member_required(login_url="admin_suite:admin_suite_login")
@require_POST
def api_send_test(request: HttpRequest, slug: str):
    """
    Minimal placeholder view used for internal smoke checks. Staff-only to avoid exposing test endpoints publicly.
    """
    if not request.user.is_staff:
        raise Http404()
    return JsonResponse({"ok": True, "slug": slug})


__all__ = ["get_settings", "api_send_test"]
