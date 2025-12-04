
from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from apps.ai import api


@require_GET
def settings_view(request):
    return JsonResponse(api.settings_snapshot())


@require_GET
def models_view(request):
    kind = request.GET.get("kind")
    return JsonResponse(api.models(kind))


@csrf_exempt
@require_http_methods(["POST"])
def execute_view(request):
    payload = json.loads(request.body or "{}")
    # Backwards compatibility: accept {action,payload} as well
    workflow = payload.get("workflow") or payload.get("action") or "default"
    inputs = payload.get("input") or payload.get("payload") or {}
    run = api.execute(workflow, inputs, request.user if hasattr(request, "user") else None)
    return JsonResponse({"ok": True, "run_id": run.id, "status": run.status, "output": run.output_payload})


