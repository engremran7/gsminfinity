# apps/core/views.py
"""
Core views — Enterprise-grade, Django 5.2+ ready.

Hardened to:
 - never return async/coroutine objects
 - never leak errors from ORM calls in async event loops
 - return only serializable objects to templates
 - load only existing templates safely
 - provide fully brand-neutral, tenant-safe site settings snapshot
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict, Iterable, List, Optional

import django
from django.core.cache import cache
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils.timezone import now, timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

# Snapshot cache keys
_SITE_SETTINGS_SNAPSHOT_KEY = "core_site_settings_snapshot_v1"
_SITE_SETTINGS_VERSION_KEY = "site_settings_version"

# Valid home templates
_HOME_TEMPLATE_PRIORITY: List[str] = ["home.html", "core/home.html"]
MAX_QUESTION_CHARS = 4_000


# ============================================================
# INTERNAL UTILITIES
# ============================================================
def _safe_count(q: Any) -> int:
    """Safe count for any queryset or iterable."""
    try:
        qs = q() if callable(q) else q
        if qs is None:
            return 0
        if hasattr(qs, "count"):
            return int(qs.count())
        return int(len(qs))
    except Exception as exc:
        logger.debug("_safe_count fallback 0: %s", exc)
        return 0


def _safe_iter(q: Any, limit: int = 5) -> list:
    """Safe slice/iteration over queryset or iterable."""
    try:
        qs = q() if callable(q) else q
        if qs is None:
            return []
        if hasattr(qs, "order_by"):
            return list(qs.order_by("-created_at")[:limit])
        return list(qs)[:limit]
    except Exception as exc:
        logger.debug("_safe_iter fallback empty: %s", exc)
        return []


# ============================================================
# SNAPSHOT OF SITE SETTINGS (BRAND-NEUTRAL)
# ============================================================
def _get_site_settings_snapshot() -> Dict[str, Any]:
    """
    Returns a fully serializable dict for templates.
    Never returns ORM objects and never raises.
    """

    # Versioned cache key
    try:
        version = cache.get(_SITE_SETTINGS_VERSION_KEY) or 0
        key = f"{_SITE_SETTINGS_SNAPSHOT_KEY}_v{version}"
    except Exception:
        key = _SITE_SETTINGS_SNAPSHOT_KEY

    # Load from cache
    try:
        payload = cache.get(key)
        if payload:
            return payload
    except Exception:
        payload = None

    # Build snapshot
    try:
        from apps.site_settings.models import SiteSettings  # type: ignore

        obj = (
            SiteSettings.get_solo()
            if hasattr(SiteSettings, "get_solo")
            else SiteSettings.objects.first()
        )

        payload = {
            "site_name": getattr(obj, "site_name", "Site"),
            "site_header": getattr(obj, "site_header", "Admin"),
            "site_description": getattr(obj, "site_description", ""),
            "enable_signup": bool(getattr(obj, "enable_signup", True)),
            "require_mfa": bool(getattr(obj, "require_mfa", False)),
            "maintenance_mode": bool(getattr(obj, "maintenance_mode", False)),
            # Feature toggles (admin controlled)
            "enable_tenants": bool(getattr(obj, "enable_tenants", False)),
            "enable_blog": bool(getattr(obj, "enable_blog", True)),
            "enable_blog_comments": bool(
                getattr(obj, "enable_blog_comments", True)
            ),
            "allow_user_blog_posts": bool(getattr(obj, "allow_user_blog_posts", False)),
            "allow_user_bounty_posts": bool(
                getattr(obj, "allow_user_bounty_posts", False)
            ),
            "primary_color": getattr(obj, "primary_color", "#0d6efd"),
            "secondary_color": getattr(obj, "secondary_color", "#6c757d"),
            "logo": (
                getattr(obj, "logo", None).url if getattr(obj, "logo", None) else None
            ),
            "dark_logo": (
                getattr(obj, "dark_logo", None).url
                if getattr(obj, "dark_logo", None)
                else None
            ),
            "favicon": (
                getattr(obj, "favicon", None).url
                if getattr(obj, "favicon", None)
                else None
            ),
        }
    except Exception as exc:
        logger.debug("site settings fallback: %s", exc)
        payload = {
            "site_name": "Site",
            "site_header": "Admin",
            "site_description": "",
            "enable_signup": True,
            "require_mfa": False,
            "maintenance_mode": False,
            "enable_tenants": False,
            "enable_blog": False,
            "enable_blog_comments": False,
            "primary_color": "#0d6efd",
            "secondary_color": "#6c757d",
            "logo": None,
            "dark_logo": None,
            "favicon": None,
        }

    try:
        cache.set(key, payload, timeout=300)
    except Exception:
        pass

    return payload


# ============================================================
# SAFE RENDERING WRAPPER
# ============================================================
def _render_safe(
    request: HttpRequest, template: str, context: Dict[str, Any], status: int = 200
) -> HttpResponse:
    """Completely safe render wrapper."""
    try:
        return render(request, template, context, status=status)
    except TemplateDoesNotExist as exc:
        logger.warning("Missing template: %s (%s)", template, exc)
        sn = (
            context.get("site_name")
            or context.get("site_settings", {}).get("site_name")
            or "Site"
        )
        return HttpResponse(
            f"<html><head><title>{sn}</title></head>"
            f"<body><h1>{sn}</h1><p>Content temporarily unavailable.</p></body></html>",
            status=status,
        )
    except Exception as exc:
        logger.exception("Render error for %s: %s", template, exc)
        return HttpResponseServerError("Internal server error")


def _first_existing_template(candidates: Iterable[str]) -> Optional[str]:
    """Pick first existing template (safe)."""
    for name in candidates:
        try:
            get_template(name)
            return name
        except TemplateDoesNotExist:
            continue
        except Exception:
            continue
    return None


# ============================================================
# HOME PAGE
# ============================================================
@never_cache
def home(request: HttpRequest) -> HttpResponse:
    settings_snapshot = _get_site_settings_snapshot()

    # Maintenance mode?
    if settings_snapshot.get("maintenance_mode"):
        return _render_safe(
            request,
            "errors/503.html",
            {
                "site_settings": settings_snapshot,
                "site_name": settings_snapshot.get("site_name"),
                "message": "This site is currently under maintenance.",
            },
            status=503,
        )

    # Query factories
    def _u():
        try:
            from apps.users.models import CustomUser  # type: ignore

            return CustomUser.objects.all()
        except Exception:
            return []

    def _d():
        try:
            from apps.users.models import DeviceFingerprint  # type: ignore

            return DeviceFingerprint.objects.filter(is_active=True)
        except Exception:
            return []

    def _n():
        try:
            from apps.users.models import Notification  # type: ignore

            if request.user.is_authenticated:
                return Notification.objects.filter(user=request.user, is_read=False)
            return Notification.objects.none()
        except Exception:
            return []

    def _a():
        try:
            from apps.users.models import Announcement  # type: ignore

            return Announcement.objects.filter(is_active=True)
        except Exception:
            return []

    # System info
    try:
        django_version = django.get_version()
    except Exception:
        django_version = "unknown"

    try:
        python_version = sys.version.split()[0]
    except Exception:
        python_version = "unknown"

    context = {
        "site_settings": settings_snapshot,
        "site_name": settings_snapshot.get("site_name"),
        "django_version": django_version,
        "python_version": python_version,
        "now": now(),
        "total_users": _safe_count(_u),
        "active_devices": _safe_count(_d),
        "unread_notifications": _safe_count(_n),
        "active_announcements": _safe_count(_a),
        "announcements": _safe_iter(_a, limit=5),
    }

    # Select homepage template
    template_name = _first_existing_template(_HOME_TEMPLATE_PRIORITY)
    if template_name:
        return _render_safe(request, template_name, context)

    # Ultimate fallback
    logger.error("No homepage template found among: %s", _HOME_TEMPLATE_PRIORITY)
    sn = context["site_name"]
    return HttpResponse(
        f"<html><head><title>{sn}</title></head>"
        f"<body><h1>{sn}</h1><p>Home page temporarily unavailable.</p></body></html>",
        status=503,
    )


# ============================================================
# TENANTS
# ============================================================
def tenants(request: HttpRequest) -> HttpResponse:
    # Gate tenants listing behind SiteSettings.enable_tenants
    try:
        from apps.site_settings.models import SiteSettings  # type: ignore

        ss = SiteSettings.get_solo()
        if not getattr(ss, "enable_tenants", False):
            raise Http404("Tenants listing is disabled.")
    except Http404:
        raise
    except Exception as exc:
        logger.debug("SiteSettings unavailable for tenants: %s", exc)
        raise Http404("Tenants listing is disabled.")

    try:
        from apps.site_settings.models import TenantSiteSettings  # type: ignore

        qs = TenantSiteSettings.objects.select_related("site").prefetch_related(
            "meta_tags", "verification_files"
        )
        tenants = list(qs.order_by("site__domain"))
    except Exception as exc:
        logger.debug("TenantSiteSettings unavailable: %s", exc)
        tenants = []

    return _render_safe(
        request,
        "core/tenants.html",
        {
            "site_settings": _get_site_settings_snapshot(),
            "tenants": tenants,
        },
    )


# ============================================================
# LEGAL PAGES
# ============================================================
def privacy(request: HttpRequest) -> HttpResponse:
    return _render_safe(
        request, "legal/privacy.html", {"site_settings": _get_site_settings_snapshot()}
    )


def terms(request: HttpRequest) -> HttpResponse:
    return _render_safe(
        request, "legal/terms.html", {"site_settings": _get_site_settings_snapshot()}
    )


def cookies(request: HttpRequest) -> HttpResponse:
    return _render_safe(
        request, "legal/cookies.html", {"site_settings": _get_site_settings_snapshot()}
    )


# ============================================================
# ERROR HANDLERS
# ============================================================
def error_400_view(
    request: HttpRequest, exception: Optional[Exception] = None
) -> HttpResponse:
    return _render_safe(
        request,
        "errors/400.html",
        {"site_settings": _get_site_settings_snapshot(), "error": str(exception or "")},
        status=400,
    )


def error_403_view(
    request: HttpRequest, exception: Optional[Exception] = None
) -> HttpResponse:
    return _render_safe(
        request,
        "errors/403.html",
        {"site_settings": _get_site_settings_snapshot(), "error": str(exception or "")},
        status=403,
    )


def error_404_view(
    request: HttpRequest, exception: Optional[Exception] = None
) -> HttpResponse:
    return _render_safe(
        request,
        "errors/404.html",
        {"site_settings": _get_site_settings_snapshot(), "error": str(exception or "")},
        status=404,
    )


def error_500_view(request: HttpRequest) -> HttpResponse:
    try:
        return _render_safe(
            request,
            "errors/500.html",
            {"site_settings": _get_site_settings_snapshot()},
            status=500,
        )
    except Exception:
        return HttpResponseServerError("Internal server error")


# ============================================================
# AI ASSISTANT ENDPOINT (Frontend widget)
# ============================================================
def _parse_json_body(request: HttpRequest, max_bytes: int = 64_000) -> dict:
    """Safe JSON body parser with size guard."""
    raw = request.body or b""
    if len(raw) > max_bytes:
        return {"__error__": "payload_too_large"}
    if not raw:
        return {}
    try:
        import json

        return json.loads(raw.decode("utf-8", errors="ignore"))
    except Exception:
        return {"__error__": "bad_json"}


def _enforce_ai_rate_limit(request: HttpRequest) -> Optional[JsonResponse]:
    """
    Optional per-view rate-limit hook. Integrate with middleware flags if present.
    Return a JsonResponse to short-circuit, or None to continue.
    """
    try:
        if getattr(request, "ai_rate_limited", False):
            return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)

        # Simple per-session throttle: enforce a short cooldown between requests
        session = getattr(request, "session", None)
        if session is not None:
            if not session.session_key:
                session.save()
            last = session.get("ai_last_ts")
            now_ts = timezone.now().timestamp()
            if last and (now_ts - float(last)) < 3:  # 3-second cooldown
                return JsonResponse({"ok": False, "error": "rate_limited"}, status=429)
            session["ai_last_ts"] = now_ts
            session.modified = True

        # Per-user soft cap: 10 requests per minute
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            key = f"ai_rl_user_{user.pk}"
            try:
                count = cache.get(key, 0)
                if count and int(count) >= 10:
                    return JsonResponse(
                        {"ok": False, "error": "rate_limited"}, status=429
                    )
                cache.set(key, int(count) + 1, timeout=60)
            except Exception:
                # Fail open if cache misbehaves
                pass
    except Exception:
        pass
    return None


@login_required
@require_POST
def ai_assistant_view(request: HttpRequest) -> JsonResponse:
    """
    Hardened AI assistant endpoint used by the frontend chat widget.

    Expects JSON: {"question": "<user question>"} or {"action": "generate_title", "payload": {...}}
    Returns: {"ok": true, "answer": "<assistant answer>"} or {"ok": false, "error": "..."}
    """
    payload = _parse_json_body(request)
    if payload.get("__error__"):
        return JsonResponse({"ok": False, "error": payload["__error__"]}, status=400)

    question = (payload.get("question") or "").strip()
    action = (payload.get("action") or "").strip()
    if not question and not action:
        return JsonResponse({"ok": False, "error": "empty_question"}, status=400)
    if question and len(question) > MAX_QUESTION_CHARS:
        return JsonResponse({"ok": False, "error": "question_too_long"}, status=400)

    rl_response = _enforce_ai_rate_limit(request)
    if rl_response is not None:
        return rl_response

    try:
        from apps.core import ai_client  # type: ignore

        if action:
            payload_text = ""
            try:
                payload_text = (payload.get("payload") or {}).get("text", "")
            except Exception:
                payload_text = ""
            if action == "generate_title":
                answer = ai_client.generate_title(payload_text or question, request.user)
            elif action == "generate_excerpt":
                answer = ai_client.generate_excerpt(payload_text or question, request.user)
            elif action == "generate_seo":
                answer = ai_client.generate_seo_description(payload_text or question, request.user)
            elif action == "suggest_tags":
                answer = ", ".join(ai_client.suggest_tags(payload_text or question, request.user))
            elif action in ("summarize", "summarize_comments"):
                answer = ai_client.summarize_text(payload_text or question, request.user)
            elif action == "moderate":
                answer = ai_client.moderate_text(payload_text or question, request.user)
            else:
                answer = f"AI action '{action}' processed."
        else:
            answer = ai_client.generate_answer(question=question, user=request.user)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("ai_assistant_view failed: %s", exc)
        return JsonResponse(
            {
                "ok": False,
                "error": "ai_failure",
                "message": "Assistant is temporarily unavailable.",
            },
            status=503,
        )

    return JsonResponse({"ok": True, "answer": answer}, status=200)

