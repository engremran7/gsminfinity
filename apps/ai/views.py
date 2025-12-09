
from __future__ import annotations

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

from apps.ai import api


@staff_member_required(login_url="admin_suite:admin_suite_login")
@require_GET
def settings_view(request):
    return JsonResponse(api.settings_snapshot())


@staff_member_required(login_url="admin_suite:admin_suite_login")
@require_GET
def models_view(request):
    kind = request.GET.get("kind")
    return JsonResponse(api.models(kind))


_AI_RL_MAX = 5
_AI_RL_WINDOW = 60  # seconds
_AI_MAX_BODY = 64_000  # bytes


def _parse_payload(request):
    raw = request.body or b""
    if len(raw) > _AI_MAX_BODY:
        return {"__error__": "payload_too_large"}
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {"__error__": "invalid-json"}
    except Exception:
        return {"__error__": "bad_payload"}


def _enforce_rate_limit(request):
    user = getattr(request, "user", None)
    ident = None
    if user and getattr(user, "is_authenticated", False):
        ident = f"user:{user.pk}"
    else:
        ident = f"ip:{request.META.get('REMOTE_ADDR') or 'anon'}"
    key = f"ai_exec_rl_{ident}"
    try:
        count = int(cache.get(key, 0))
        if count >= _AI_RL_MAX:
            return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)
        cache.set(key, count + 1, timeout=_AI_RL_WINDOW)
    except Exception:
        # Fail open on cache errors
        pass
    return None


@csrf_protect
@login_required
@require_http_methods(["POST"])
def execute_view(request):
    payload = _parse_payload(request)
    if payload.get("__error__"):
        status = 413 if payload["__error__"] == "payload_too_large" else 400
        return JsonResponse({"ok": False, "error": payload["__error__"]}, status=status)
    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)

    rl_response = _enforce_rate_limit(request)
    if rl_response:
        return rl_response

    # Backwards compatibility: accept {action,payload} as well
    workflow = payload.get("workflow") or payload.get("action") or "default"
    inputs = payload.get("input") or payload.get("payload") or {}
    if not isinstance(inputs, dict):
        return JsonResponse({"ok": False, "error": "bad_payload"}, status=400)
    run = api.execute(
        workflow,
        inputs,
        request.user if hasattr(request, "user") and request.user.is_authenticated else None,
    )
    return JsonResponse({"ok": True, "run_id": run.id, "status": run.status, "output": run.output_payload})


