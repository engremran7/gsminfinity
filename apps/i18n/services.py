
from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
from django.http import HttpRequest
from django.utils.translation import get_language_from_request, to_locale

from apps.i18n.models import (
    AppManifest,
    AuditLog,
    FontRegistry,
    LanguageProfile,
    Locale,
    MissingKeyLog,
    Theme,
    ThemeAssignment,
    TranslationKey,
    TranslationValue,
)

logger = logging.getLogger(__name__)

# Sensible defaults to avoid empty payloads when DB/theme data is missing
FALLBACK_TOKENS = {
    "light": {
        "color": {
            "surface": "#ffffff",
            "muted": "#475569",
            "text": "#0f172a",
            "border": "#e2e8f0",
            "primary": "#0d6efd",
            "accent": "#10b981",
        },
        "radii": {"md": "12px"},
        "shadows": {"elevation": "0 10px 30px rgba(15,23,42,0.15)"},
        "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
    },
    "dark": {
        "color": {
            "surface": "#0f172a",
            "muted": "#94a3b8",
            "text": "#e2e8f0",
            "border": "#1f2937",
            "primary": "#38bdf8",
            "accent": "#f472b6",
        },
        "radii": {"md": "12px"},
        "shadows": {"elevation": "0 12px 36px rgba(0,0,0,0.55)"},
        "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
    },
    "high_contrast": {
        "color": {
            "surface": "#000000",
            "muted": "#d1d5db",
            "text": "#ffffff",
            "border": "#ffffff",
            "primary": "#ffbf00",
            "accent": "#00ffcc",
        },
        "radii": {"md": "0px"},
        "shadows": {"elevation": "none"},
        "typography": {"fonts": {"base": "Inter, 'Segoe UI', system-ui, sans-serif"}},
    },
}


# ---------------------------------------------------------------------------
# Locale resolution
# ---------------------------------------------------------------------------
def resolve_locale(request: HttpRequest, app_id: str, site_id: Optional[str] = None) -> str:
    """
    Resolve locale following preference order:
    1. user preference (request.user.profile.locale if exists)
    2. query param / URL override (?lang=)
    3. language cookie (LANGUAGE_COOKIE_NAME)
    4. app/site default
    5. Accept-Language (normalized)
    6. platform fallback (en)
    """
    supported = set(Locale.objects.values_list("code", flat=True))

    def _is_supported(code: str) -> bool:
        return code and code in supported

    # 1) explicit user pref
    try:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False) and getattr(user, "locale", None):
            if _is_supported(user.locale):
                return user.locale
    except Exception:
        pass

    # 2) query / header override
    lang_param = request.GET.get("lang") or request.META.get("HTTP_X_LANG")
    if lang_param:
        if _is_supported(lang_param):
            return lang_param

    # 3) cookie (Django language cookie or custom "lang")
    try:
        lang_cookie = request.COOKIES.get(getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")) or request.COOKIES.get("lang")
        if lang_cookie and _is_supported(lang_cookie):
            return lang_cookie
    except Exception:
        pass

    # 4) app/site default
    try:
        lp = LanguageProfile.objects.filter(app_id=app_id, site_id=site_id).first()
        if lp and lp.default_locale:
            if _is_supported(lp.default_locale):
                return lp.default_locale
    except Exception:
        pass

    # 5) accept language (normalized)
    try:
        lang = get_language_from_request(request)
        if lang:
            lang_norm = to_locale(lang)
            if _is_supported(lang_norm):
                return lang_norm
            if "-" in lang_norm:
                base = lang_norm.split("-")[0]
                if _is_supported(base):
                    return base
    except Exception:
        pass

    return "en"


def _direction_for_locale(locale_code: str) -> str:
    try:
        loc = Locale.objects.filter(code=locale_code).first()
        if loc:
            return loc.direction
    except Exception:
        pass
    # Urdu + Arabic defaults
    if locale_code.startswith(("ar", "ur", "fa", "ps")):
        return "rtl"
    return "ltr"


# ---------------------------------------------------------------------------
# Translation resolution
# ---------------------------------------------------------------------------
def get_bundle(app_id: str, locale: str, namespaces: Iterable[str] | None = None, since_version: int | None = None) -> Dict[str, Any]:
    """
    Return a translation bundle with safe fallback when DB lookups fail.
    """
    ns_list = list(namespaces) if namespaces else []
    cache_key = f"i18n_bundle:{app_id}:{locale}:{','.join(sorted(ns_list))}:{since_version or 0}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        values: Dict[str, str] = {}
        qs = TranslationKey.objects.filter(app_id=app_id)
        if ns_list:
            qs = qs.filter(namespace__in=ns_list)
        if since_version:
            qs = qs.filter(version__gt=since_version)

        key_map = {k.id: f"{k.namespace}.{k.key}" for k in qs.select_related(None)}
        val_qs = TranslationValue.objects.filter(
            translation_key_id__in=key_map.keys(), locale=locale, status="approved"
        )
        for val in val_qs:
            values[key_map.get(val.translation_key_id, "")] = val.message

        bundle = {
            "app_id": app_id,
            "locale": locale,
            "values": values,
            "version": max((k.version for k in qs), default=1),
            "direction": _direction_for_locale(locale),
        }
        cache.set(cache_key, bundle, timeout=60)
        return bundle
    except Exception as exc:
        logger.warning("i18n bundle fallback for %s/%s: %s", app_id, locale, exc)
        fallback = {"app_id": app_id, "locale": locale, "values": {}, "version": 1, "direction": _direction_for_locale(locale)}
        cache.set(cache_key, fallback, timeout=30)
        return fallback


def resolve_key(app_id: str, locale: str, key: str, default: str = "", log_missing: bool = True, site_id: str | None = None) -> str:
    """
    Resolve a single key with fallback chain.
    """
    namespace, sep, key_name = key.partition(".")
    if not sep:
        namespace = "common"
        key_name = key

    tk = TranslationKey.objects.filter(app_id=app_id, namespace=namespace, key=key_name).first()
    if not tk:
        if log_missing:
            MissingKeyLog.objects.create(app_id=app_id, site_id=site_id, locale=locale, key=key_name)
        return default or key

    # primary locale
    tv = TranslationValue.objects.filter(translation_key=tk, locale=locale, status="approved").first()
    if tv:
        return tv.message

    # fallback to app default
    fallback_locale = None
    lp = LanguageProfile.objects.filter(app_id=app_id, site_id=site_id).first()
    if lp:
        fallback_locale = lp.fallback_locale or lp.default_locale
    if fallback_locale:
        tv = TranslationValue.objects.filter(translation_key=tk, locale=fallback_locale, status="approved").first()
        if tv:
            return tv.message

    # global default
    tv = TranslationValue.objects.filter(translation_key=tk, locale="en", status="approved").first()
    if tv:
        return tv.message

    if log_missing:
        MissingKeyLog.objects.create(app_id=app_id, site_id=site_id, locale=locale, key=key_name)
    return default or key


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------
def resolve_theme(app_id: str, locale: str, site_id: str | None = None, route: str | None = None, user_id: str | None = None, device_pref: str | None = None, system_pref: str | None = None) -> Dict[str, Any]:
    """
    Merge tokens with inheritance and locale overrides, respecting assignments.
    """
    cache_key = f"i18n_theme:{app_id}:{locale}:{site_id or 'global'}:{route or ''}:{user_id or ''}:{device_pref or ''}:{system_pref or ''}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    assignments = ThemeAssignment.objects.filter(app_id=app_id)
    if site_id:
        assignments = assignments.filter(models.Q(site_id=site_id) | models.Q(site_id__isnull=True))

    # Deterministic priority order: user > route > device > system > site > global
    # Use latest updated assignment per bucket to avoid random .first() behavior
    def _latest(qs):
        return qs.order_by("-id").first()

    def _mode_from_pref():
        for pref in (device_pref, system_pref):
            if not pref:
                continue
            pref_l = str(pref).lower()
            if pref_l in {"light", "dark", "high_contrast"}:
                return pref_l
            # accept browser values
            if pref_l in {"light", "dark"}:
                return pref_l
        return None

    desired_mode = _mode_from_pref()

    assignment = (
        _latest(assignments.filter(user_id=user_id))  # user-scoped
        or (route and _latest(assignments.filter(route=route)))  # route-scoped
        or (device_pref and _latest(assignments.filter(device_pref=device_pref)))  # device pref
        or (system_pref and _latest(assignments.filter(system_pref=system_pref)))  # system pref
        or _latest(assignments.filter(scope="site", site_id=site_id))  # explicit site
        or _latest(assignments.filter(scope="global"))  # global fallback
    )

    theme = assignment.theme if assignment else None

    # Fallback: choose theme matching desired mode if provided
    if not theme and desired_mode:
        theme = (
            Theme.objects.filter(app_id=app_id, site_id=site_id, mode=desired_mode).first()
            or Theme.objects.filter(app_id=app_id, mode=desired_mode).first()
        )

    if not theme:
        theme = Theme.objects.filter(app_id=app_id, site_id=site_id).first()

    if not theme:
        return _fallback_theme_payload(locale, desired_mode or "light")

    tokens = _merge_theme_tokens(theme)
    locale_overrides = theme.locale_overrides or {}
    if locale in locale_overrides:
        tokens = _deep_merge(tokens, locale_overrides[locale])

    tokens.setdefault("typography", {})
    tokens["typography"].setdefault("fonts", {})
    tokens["typography"]["direction"] = _direction_for_locale(locale)

    # Apply default font registry for locale, if configured
    try:
        font = (
            FontRegistry.objects.filter(is_default_for_locales__contains=[locale]).first()
            or FontRegistry.objects.filter(is_default_for_locales__contains=[locale.split("-")[0]]).first()
        )
        if font:
            tokens["typography"]["fonts"].setdefault("base", font.family)
            tokens["typography"]["fonts"].setdefault("heading", font.family)
    except Exception:
        pass

    result = {"theme": theme.name, "mode": theme.mode, "tokens": tokens, "direction": tokens["typography"]["direction"]}
    cache.set(cache_key, result, timeout=60)
    return result


def _merge_theme_tokens(theme: Theme) -> Dict[str, Any]:
    if not theme.inherits_from:
        return theme.tokens or {}
    parent_tokens = _merge_theme_tokens(theme.inherits_from)
    return _deep_merge(parent_tokens, theme.tokens or {})


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _fallback_theme_payload(locale: str, mode: str = "light") -> Dict[str, Any]:
    """
    Provide a deterministic theme payload when DB lookups fail.
    """
    tokens = FALLBACK_TOKENS.get(mode) or FALLBACK_TOKENS["light"]
    tokens = dict(tokens)
    tokens.setdefault("typography", {})
    tokens["typography"]["direction"] = _direction_for_locale(locale)
    return {"theme": "fallback", "mode": mode, "tokens": tokens, "direction": tokens["typography"]["direction"]}


# ---------------------------------------------------------------------------
# App manifest + audit
# ---------------------------------------------------------------------------
def register_manifest(app_id: str, site_id: str | None, namespaces: list[str], supported_locales: list[str], default_locale: str, token_usage: list[str], routes: list[str], actor=None) -> AppManifest:
    with transaction.atomic():
        manifest, _ = AppManifest.objects.update_or_create(
            app_id=app_id,
            defaults={
                "site_id": site_id,
                "namespaces": namespaces,
                "supported_locales": supported_locales,
                "default_locale": default_locale,
                "token_usage": token_usage,
                "routes": routes,
                "version": models.F("version") + 1,
            },
        )
        _audit(actor, "manifest_updated", app_id, after={"namespaces": namespaces, "supported_locales": supported_locales})
        return manifest


def _audit(actor, action: str, app_id: str, before: dict | None = None, after: dict | None = None) -> None:
    try:
        AuditLog.objects.create(actor=actor, action=action, app_id=app_id, before=before or {})
    except Exception:
        return


# ---------------------------------------------------------------------------
# Auto-translate hook (integration ready for external provider)
# ---------------------------------------------------------------------------
def auto_translate(app_id: str, key: TranslationKey, target_locale: str, provider: str | None = None) -> Optional[TranslationValue]:
    """
    Auto-translate a TranslationKey to target_locale using the configured provider.
    
    Args:
        app_id: Application identifier
        key: TranslationKey to translate
        target_locale: Target locale code (e.g., 'ar', 'fr', 'de')
        provider: Optional provider override ('deepl', 'argos', 'ai')
        
    Returns:
        TranslationValue if successful, None otherwise
    """
    try:
        from django.conf import settings

        from apps.i18n.translation_provider import get_translator

        # Get source text from English or default locale
        source_value = TranslationValue.objects.filter(
            translation_key=key,
            locale__in=['en', 'en-US'],
            status='approved'
        ).first()

        if not source_value:
            logger.warning(f"No source translation found for key {key.key}")
            return None

        # Get configured provider
        provider_name = provider or getattr(settings, 'TRANSLATION_PROVIDER', 'dummy')
        translator = get_translator(provider_name)

        if not translator:
            logger.warning(f"Translation provider '{provider_name}' not available")
            return None

        # Translate
        translated_text = translator.translate(
            text=source_value.message,
            source_lang='en',
            target_lang=target_locale
        )

        if not translated_text:
            return None

        # Create or update translation value
        trans_value, created = TranslationValue.objects.update_or_create(
            translation_key=key,
            locale=target_locale,
            defaults={
                'message': translated_text,
                'status': 'pending',  # Auto-translated content needs review
            }
        )

        # Invalidate cache
        cache_key = f"i18n_bundle:{app_id}:{target_locale}:*"
        cache.delete_pattern(cache_key) if hasattr(cache, 'delete_pattern') else cache.clear()

        logger.info(f"Auto-translated key '{key.key}' to {target_locale}")
        return trans_value

    except Exception as e:
        logger.error(f"Auto-translate failed for key {key.key}: {e}")
        return None


def auto_translate_batch(app_id: str, target_locale: str, namespace: str | None = None, limit: int = 100) -> dict:
    """
    Batch auto-translate missing translations for a locale.
    
    Args:
        app_id: Application identifier
        target_locale: Target locale to translate to
        namespace: Optional namespace filter
        limit: Maximum keys to process
        
    Returns:
        Dict with success/failure counts
    """
    results = {'translated': 0, 'failed': 0, 'skipped': 0}

    try:
        # Find keys missing translations for target locale
        qs = TranslationKey.objects.filter(app_id=app_id)
        if namespace:
            qs = qs.filter(namespace=namespace)

        keys_with_target = TranslationValue.objects.filter(
            locale=target_locale
        ).values_list('translation_key_id', flat=True)

        missing_keys = qs.exclude(id__in=keys_with_target)[:limit]

        for key in missing_keys:
            result = auto_translate(app_id, key, target_locale)
            if result:
                results['translated'] += 1
            else:
                results['failed'] += 1

        logger.info(f"Batch translate to {target_locale}: {results}")
        return results

    except Exception as e:
        logger.error(f"Batch translate failed: {e}")
        results['error'] = str(e)
        return results


__all__ = [
    "resolve_locale",
    "get_bundle",
    "resolve_key",
    "resolve_theme",
    "register_manifest",
    "auto_translate",
    "auto_translate_batch",
]


