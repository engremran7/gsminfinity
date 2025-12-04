
from __future__ import annotations

import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

from apps.ai import api


@require_GET
def settings_view(request):
    return JsonResponse(api.settings_snapshot())


@require_GET
def models_view(request):
    kind = request.GET.get("kind")
    return JsonResponse(api.models(kind))


@csrf_protect
@require_http_methods(["POST"])
def execute_view(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    # Backwards compatibility: accept {action,payload} as well
    workflow = payload.get("workflow") or payload.get("action") or "default"
    inputs = payload.get("input") or payload.get("payload") or {}
    if not isinstance(inputs, dict):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    run = api.execute(workflow, inputs, request.user if hasattr(request, "user") else None)
    return JsonResponse({"ok": True, "run_id": run.id, "status": run.status, "output": run.output_payload})


