"""
apps.consent.views
==================

Enterprise-grade GDPR / CCPA consent management views.
Hardened, deterministic, free from unsafe fallbacks.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.template import TemplateDoesNotExist
from django.views.decorators.http import require_GET, require_POST

from apps.consent.models import ConsentRecord, ConsentPolicy
from apps.consent.utils import consent_cache_key, get_active_policy, resolve_site_domain

logger = logging.getLogger(__name__)


# ============================================================================
# INTERNAL UTILITIES
# ============================================================================

def hx_response(content: str = "", status: int = 200, triggers: Optional[dict] = None) -> HttpResponse:
    """HTMX-safe response helper with HX-Trigger."""
    resp = HttpResponse(content, status=status)
    if triggers:
        try:
            resp["HX-Trigger"] = json.dumps(triggers)
        except Exception:
            logger.debug("hx_response: HX-Trigger serialization failed")
    return resp


def _is_htmx_or_ajax(request: HttpRequest) -> bool:
    """Detect HTMX or AJAX request."""
    try:
        if request.headers.get("HX-Request"):
            return True
        return request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest"
    except Exception:
        return False


def _parse_json(request: HttpRequest, max_bytes: int = 1_048_576) -> Dict[str, Any]:
    try:
        raw = request.body or b""
        if len(raw) > max_bytes:
            return {"__error__": "payload_too_large"}
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8", errors="ignore"))
    except Exception:
        return {}


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _ensure_session(request: HttpRequest) -> Optional[str]:
    """Guarantee a valid session key for anonymous users."""
    try:
        if not getattr(request, "session", None):
            return None
        if not request.session.session_key:
            request.session.create()
        return request.session.session_key
    except Exception:
        return None


def _domain(request: HttpRequest) -> str:
    """Unified domain resolver."""
    try:
        return resolve_site_domain(request) or get_current_site(request).domain or request.get_host()
    except Exception:
        return request.get_host()


def _active_policy(request: HttpRequest) -> Optional[Dict[str, Any]]:
    """Resolve the active policy safely with cache + ORM fallback."""
    try:
        domain = _domain(request)
        key = consent_cache_key(domain)

        cached = cache.get(key)
        if cached is not None:
            return cached

        # helper
        try:
            payload = get_active_policy(domain)
            if payload:
                ttl = int(payload.get("cache_ttl_seconds", getattr(settings, "CONSENT_POLICY_CACHE_TTL", 300)))
                cache.set(key, payload, timeout=ttl)
                return payload
        except Exception:
            pass

        # ORM
        obj = (
            ConsentPolicy.objects.filter(is_active=True, site_domain=domain)
            .order_by("-created_at")
            .first()
        )
        if not obj:
            return None

        payload = {
            "version": str(obj.version or ""),
            "categories_snapshot": obj.categories_snapshot or {},
            "banner_text": obj.banner_text or "",
            "manage_text": obj.manage_text or "",
            "is_active": obj.is_active,
            "site_domain": domain,
            "cache_ttl_seconds": int(getattr(obj, "cache_ttl_seconds",
                                             getattr(settings, "CONSENT_POLICY_CACHE_TTL", 300))),
        }
        cache.set(key, payload, timeout=payload["cache_ttl_seconds"])
        return payload

    except Exception as exc:
        logger.exception("_active_policy failed -> %s", exc)
        return None


# ============================================================================
# BANNER
# ============================================================================

@require_GET
def banner_partial(request: HttpRequest) -> HttpResponse:
    """Render banner safely with multi-template fallback."""
    try:
        policy = _active_policy(request)
        if not policy:
            return HttpResponse("", content_type="text/html")

        # If user accepted everything earlier
        if getattr(request, "session", None) and request.session.get("consent_all_accepted"):
            return HttpResponse("", content_type="text/html")

        snapshot = policy.get("categories_snapshot", {}) or {}

        # Build categories
        categories = {
            slug: {
                "name": meta.get("name", slug.replace("_", " ").title()),
                "required": bool(meta.get("required")),
                "accepted": bool(meta.get("required") or meta.get("default", False)),
            }
            for slug, meta in snapshot.items()
        }

        # Fallback (minimal required cookie)
        if not categories:
            categories = {
                "functional": {"name": "Functional", "required": True, "accepted": True}
            }

        ctx = {
            "consent_active": True,
            "consent_version": policy.get("version", ""),
            "consent_text": policy.get("banner_text", ""),
            "consent_categories": categories,
            "csrf_token": get_token(request),
        }

        for tpl in [
            "consent/includes/banner.html",
            "includes/banner.html",
            "consent/banner.html",
        ]:
            try:
                return TemplateResponse(request, tpl, ctx)
            except TemplateDoesNotExist:
                continue
            except Exception as exc:
                logger.exception("banner render error -> %s", exc)
                return HttpResponse("", content_type="text/html")

        return HttpResponse("", content_type="text/html")

    except Exception as exc:
        logger.exception("banner_partial failed -> %s", exc)
        return HttpResponse("", content_type="text/html")


# ============================================================================
# CONSENT MANAGEMENT PAGE
# ============================================================================

@require_GET
def manage_consent(request: HttpRequest) -> HttpResponse:
    try:
        policy = _active_policy(request)
        snapshot = (policy or {}).get("categories_snapshot", {}) or {}

        categories = [
            {
                "name": meta.get("name", slug.replace("_", " ").title()),
                "slug": slug,
                "description": meta.get("description", ""),
                "required": bool(meta.get("required")),
                "accepted": bool(meta.get("required") or meta.get("default", False)),
            }
            for slug, meta in snapshot.items()
        ]

        if not categories:
            categories = [
                {"name": "Functional", "slug": "functional", "required": True, "accepted": True},
                {"name": "Analytics", "slug": "analytics", "required": False, "accepted": False},
            ]

        return render(
            request,
            "site_settings/consent_manage.html",
            {
                "consent_active": bool(policy),
                "consent_version": (policy or {}).get("version", ""),
                "consent_text": (policy or {}).get("manage_text", ""),
                "categories": categories,
            },
        )

    except Exception as exc:
        logger.exception("manage_consent failed -> %s", exc)
        return render(request, "site_settings/consent_manage.html", {"categories": []})


# ============================================================================
# STATUS ENDPOINT (HTML/JS)
# ============================================================================

@require_GET
def consent_status(request: HttpRequest) -> JsonResponse:
    """HTML/JS-safe status endpoint (NOT the API version)."""
    try:
        policy = _active_policy(request)
        if not policy:
            return JsonResponse({"error": "no_active_policy"}, status=404)

        snapshot = policy.get("categories_snapshot", {}) or {}

        categories = {
            slug: {
                "name": meta.get("name", slug.replace("_", " ").title()),
                "required": bool(meta.get("required")),
                "default": bool(meta.get("default")),
                "accepted": bool(meta.get("required")),
            }
            for slug, meta in snapshot.items()
        }

        # Ensure functional
        categories.setdefault(
            "functional",
            {"name": "Functional", "required": True, "default": True, "accepted": True},
        )

        domain = _domain(request)

        # Load previous record
        rec = None
        try:
            if request.user.is_authenticated:
                rec = ConsentRecord.objects.filter(
                    user=request.user,
                    policy_version=policy["version"],
                    site_domain=domain,
                ).first()
            else:
                sk = _ensure_session(request)
                if sk:
                    rec = ConsentRecord.objects.filter(
                        session_key=sk,
                        policy_version=policy["version"],
                        site_domain=domain,
                    ).first()
        except Exception:
            rec = None

        if rec and rec.accepted_categories:
            for slug, val in rec.accepted_categories.items():
                if slug in categories and not categories[slug]["required"]:
                    categories[slug]["accepted"] = bool(val)

        return JsonResponse(
            {
                "consent_active": True,
                "consent_version": policy["version"],
                "categories": categories,
                "site_domain": domain,
            },
            json_dumps_params={"indent": 2},
        )

    except Exception as exc:
        logger.exception("consent_status failed -> %s", exc)
        return JsonResponse({"error": "internal_error"}, status=500)


# ============================================================================
# MUTATION HANDLERS
# ============================================================================

@require_POST
def consent_accept(request: HttpRequest) -> HttpResponse:
    """
    Save granular accept / accept_all / reject_all preferences.
    Unified deterministic handler.
    """
    try:
        policy = _active_policy(request)
        if not policy:
            return JsonResponse({"ok": False, "error": "no_active_policy"}, status=400)

        snapshot = policy.get("categories_snapshot", {}) or {}
        valid_slugs = set(snapshot.keys()) | {"functional"}

        # JSON or form
        if "json" in (request.content_type or "").lower():
            data = _parse_json(request)
            if data.get("__error__") == "payload_too_large":
                return JsonResponse({"error": "payload_too_large"}, status=413)
        else:
            data = request.POST.copy()

        reject_all = _bool(data.get("reject_all"))
        accept_all = _bool(data.get("accept_all"))

        # Build acceptance map
        if reject_all:
            accepted = {slug: False for slug in valid_slugs}
            accepted["functional"] = True
            for slug, meta in snapshot.items():
                if meta.get("required"):
                    accepted[slug] = True

        elif accept_all:
            accepted = {slug: True for slug in valid_slugs}

        else:
            accepted = {
                slug: True
                if slug == "functional" or snapshot.get(slug, {}).get("required")
                else _bool(data.get(slug))
                for slug in valid_slugs
            }

        sanitized = {slug: bool(v) for slug, v in accepted.items()}

        sk = _ensure_session(request)
        domain = _domain(request)

        defaults = {"accepted_categories": sanitized, "site_domain": domain, "session_key": sk}

        # Save record
        with transaction.atomic():
            if request.user.is_authenticated:
                ConsentRecord.objects.update_or_create(
                    user=request.user,
                    policy_version=policy["version"],
                    site_domain=domain,
                    defaults=defaults,
                )
            else:
                ConsentRecord.objects.update_or_create(
                    session_key=sk,
                    policy_version=policy["version"],
                    site_domain=domain,
                    defaults=defaults,
                )

        # Session flags
        try:
            if getattr(request, "session", None):
                non_required = [v for k, v in sanitized.items() if k != "functional"]
                request.session["consent_all_accepted"] = all(non_required) if non_required else True
                request.session["consent_rejected"] = not any(non_required) if non_required else False
                request.session.modified = True
        except Exception:
            pass

        msg = (
            "You have rejected all optional cookies."
            if reject_all else
            "You have accepted all optional cookies."
            if accept_all else
            "Your preferences have been saved."
        )

        # JSON response
        if "json" in (request.content_type or "").lower() and _is_htmx_or_ajax(request):
            return JsonResponse(
                {
                    "ok": True,
                    "message": msg,
                    "consent": sanitized,
                    "hx_trigger": {"showToast": {"html": msg}},
                },
                json_dumps_params={"indent": 2},
            )

        # HTMX
        if _is_htmx_or_ajax(request):
            toast_html = render_to_string("partials/toast_fragment.html", {"message": msg})
            return hx_response("", triggers={"removeConsentBanner": True, "showToast": {"html": toast_html}})

        messages.success(request, msg)
        return redirect(data.get("next") or "/")

    except Exception as exc:
        logger.exception("consent_accept failed -> %s", exc)
        if _is_htmx_or_ajax(request):
            return JsonResponse({"ok": False, "error": "internal_error"}, status=500)
        messages.error(request, "Unexpected error while saving preferences.")
        return redirect("/")


@require_POST
def consent_accept_all(request: HttpRequest) -> HttpResponse:
    """Accept all optional categories."""
    try:
        policy = _active_policy(request)
        if not policy:
            return JsonResponse({"error": "no_active_policy"}, status=400)

        snapshot = policy.get("categories_snapshot", {}) or {}
        valid_slugs = set(snapshot.keys()) | {"functional"}

        sanitized = {slug: True for slug in valid_slugs}

        sk = _ensure_session(request)
        domain = _domain(request)

        defaults = {"accepted_categories": sanitized, "site_domain": domain, "session_key": sk}

        with transaction.atomic():
            if request.user.is_authenticated:
                ConsentRecord.objects.update_or_create(
                    user=request.user,
                    policy_version=policy["version"],
                    site_domain=domain,
                    defaults=defaults,
                )
            else:
                ConsentRecord.objects.update_or_create(
                    session_key=sk,
                    policy_version=policy["version"],
                    site_domain=domain,
                    defaults=defaults,
                )

        try:
            if getattr(request, "session", None):
                request.session["consent_all_accepted"] = True
                request.session["consent_rejected"] = False
                request.session.modified = True
        except Exception:
            pass

        msg = "You have accepted all optional cookies."

        if _is_htmx_or_ajax(request):
            toast_html = render_to_string("partials/toast_fragment.html", {"message": msg})
            return hx_response("", triggers={"removeConsentBanner": True, "showToast": {"html": toast_html}})

        messages.success(request, msg)
        return redirect(request.POST.get("next") or "/")

    except Exception as exc:
        logger.exception("consent_accept_all failed -> %s", exc)
        return JsonResponse({"error": "internal_error"}, status=500)


@require_POST
def consent_reject_all(request: HttpRequest) -> HttpResponse:
    """Reject all optional categories."""
    try:
        policy = _active_policy(request)
        if not policy:
            return JsonResponse({"error": "no_active_policy"}, status=400)

        snapshot = policy.get("categories_snapshot", {}) or {}
        valid_slugs = set(snapshot.keys()) | {"functional"}

        accepted = {slug: False for slug in valid_slugs}
        accepted["functional"] = True

        for slug, meta in snapshot.items():
            if meta.get("required"):
                accepted[slug] = True

        sanitized = {k: bool(v) for k, v in accepted.items()}

        sk = _ensure_session(request)
        domain = _domain(request)

        defaults = {"accepted_categories": sanitized, "site_domain": domain, "session_key": sk}

        with transaction.atomic():
            if request.user.is_authenticated:
                ConsentRecord.objects.update_or_create(
                    user=request.user,
                    policy_version=policy["version"],
                    site_domain=domain,
                    defaults=defaults,
                )
            else:
                ConsentRecord.objects.update_or_create(
                    session_key=sk,
                    policy_version=policy["version"],
                    site_domain=domain,
                    defaults=defaults,
                )

        try:
            if getattr(request, "session", None):
                request.session["consent_all_accepted"] = False
                request.session["consent_rejected"] = True
                request.session.modified = True
        except Exception:
            pass

        msg = "You rejected optional cookies."

        if _is_htmx_or_ajax(request):
            toast_html = render_to_string("partials/toast_fragment.html", {"message": msg})
            return hx_response("", triggers={"removeConsentBanner": True, "showToast": {"html": toast_html}})

        messages.success(request, msg)
        return redirect(request.POST.get("next") or "/")

    except Exception as exc:
        logger.exception("consent_reject_all failed -> %s", exc)
        return JsonResponse({"error": "internal_error"}, status=500)
