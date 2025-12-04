
from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.app_registry import api


@require_GET
def registry_list(request):
    return JsonResponse({"apps": api.list_registry()})


@require_GET
def registry_detail(request, app_id: str):
    entry = api.registry_entry(app_id)
    if not entry:
        return JsonResponse({"error": "not_found"}, status=404)
    return JsonResponse(entry)


