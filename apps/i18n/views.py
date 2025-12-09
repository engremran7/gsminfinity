
from __future__ import annotations

import json
from typing import Any, Dict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseBadRequest
import logging
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.decorators.csrf import csrf_protect

from apps.i18n.api import bundle, locale_for_request, register_manifest, theme_for_request
from apps.i18n.models import LanguageProfile, Locale
from apps.i18n.translation_provider import get_translator

logger = logging.getLogger(__name__)


@require_GET
def bundle_view(request):
    try:
        app_id = request.GET.get("app_id") or ""
        locale = request.GET.get("locale") or locale_for_request(request, app_id)
        namespaces = request.GET.getlist("namespace") or None
        since = request.GET.get("since_version")
        since_version = int(since) if since else None
        data = bundle(app_id, locale, namespaces, since_version)
        return JsonResponse(data)
    except Exception as exc:
        logger.warning("bundle_view fallback: %s", exc)
        return JsonResponse({"app_id": "", "locale": "en", "values": {}, "version": 1, "direction": "ltr"}, status=200)


@require_GET
def theme_view(request):
    try:
        app_id = request.GET.get("app_id") or ""
        site_id = request.GET.get("site_id") or None
        route = request.GET.get("route") or request.path
        data = theme_for_request(request, app_id, site_id=site_id, route=route)
        return JsonResponse(data)
    except Exception as exc:
        logger.warning("theme_view fallback: %s", exc)
        return JsonResponse({"theme": "fallback", "mode": "light", "tokens": {}, "direction": "ltr"}, status=200)


def _staff_required(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(_staff_required)
@require_http_methods(["POST"])
def manifest_view(request):
    """
    Protected endpoint to register/update app manifests.
    Validates app_id, locales, and namespaces against configured profiles/locales.
    """
    try:
        payload: Dict[str, Any] = json.loads(request.body or "{}")
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    app_id = (payload.get("app_id") or "").strip()
    if not app_id:
        return HttpResponseBadRequest("app_id is required")

    site_id = (payload.get("site_id") or None) or None
    namespaces = payload.get("namespaces", []) or []
    if not isinstance(namespaces, list):
        return HttpResponseBadRequest("namespaces must be a list")

    supported_locales = payload.get("supported_locales", []) or []
    if not isinstance(supported_locales, list):
        return HttpResponseBadRequest("supported_locales must be a list")

    default_locale = (payload.get("default_locale") or "en").strip()
    routes = payload.get("routes", []) or []
    token_usage = payload.get("token_usage", []) or []

    # Validate locales against Locale table
    allowed_locale_codes = set(Locale.objects.values_list("code", flat=True))
    invalid_locales = [l for l in supported_locales if l not in allowed_locale_codes]
    if invalid_locales:
        return HttpResponseBadRequest(f"Unsupported locales: {', '.join(invalid_locales)}")
    if default_locale not in allowed_locale_codes:
        return HttpResponseBadRequest(f"Default locale {default_locale} is not supported")

    # Validate app_id/site_id combo exists or will exist in LanguageProfile
    lp = LanguageProfile.objects.filter(app_id=app_id, site_id=site_id).first()
    if lp:
        # Use profile defaults if payload omitted supported_locales
        if not supported_locales:
            supported_locales = lp.supported_locales or []
        if not default_locale:
            default_locale = lp.default_locale

    manifest = register_manifest(
        app_id=app_id,
        site_id=site_id,
        namespaces=namespaces,
        supported_locales=supported_locales,
        default_locale=default_locale,
        token_usage=token_usage,
        routes=routes,
        actor=getattr(request, "user", None),
    )
    return JsonResponse({"ok": True, "version": manifest.version})


@require_POST
@csrf_protect
def translate_texts(request):
    """
    Lightweight translation endpoint using configured provider.
    Accepts: text (str or list), target, optional source.
    """
    target = (request.POST.get("target") or "").strip()
    source = (request.POST.get("source") or "").strip() or None
    texts = request.POST.getlist("text")
    if not texts:
        single = request.POST.get("text")
        if single:
            texts = [single]
    if not texts or not target:
        return JsonResponse({"error": "text_and_target_required"}, status=400)
    translator = get_translator()
    translated = translator.translate(texts, target=target, source=source)
    return JsonResponse({"items": translated})


