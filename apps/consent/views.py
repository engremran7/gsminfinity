# apps/consent/views.py
"""
apps.consent.views
------------------
Enterprise-grade GDPR/CCPA consent management views.

✅ Features:
- Banner + Manage Consent UI rendering
- JSON API for SPA consent state
- Atomic persistence for consent updates
- Per-site active policy resolution
- CSRF and body-size protection
- Safe JSON parsing and transaction handling
"""

import logging
import json
from typing import Any, Dict, Optional

from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse
from django.http import JsonResponse, HttpRequest
from django.db import transaction
from django.core.cache import cache

from apps.consent.models import ConsentPolicy, ConsentRecord

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _is_ajax_request(request: HttpRequest) -> bool:
    """Portable check for AJAX or JSON requests."""
    hdr = request.headers.get("x-requested-with", "")
    return hdr == "XMLHttpRequest" or (request.content_type or "").startswith("application/json")


def _get_active_policy(request: Optional[HttpRequest] = None) -> Optional[ConsentPolicy]:
    """
    Retrieve the per-site active ConsentPolicy using cache and DB fallback.
    """
    try:
        site_domain = getattr(get_current_site(request), "domain", None) or getattr(request, "get_host", lambda: "global")()
        cache_key = f"active_consent_policy_{site_domain}"
        policy = cache.get(cache_key)
        if not policy:
            policy = (
                ConsentPolicy.objects.filter(is_active=True, site_domain=site_domain)
                .order_by("-created_at")
                .first()
            )
            if policy:
                ttl = getattr(policy, "cache_ttl_seconds", 300) or 300
                cache.set(cache_key, policy, timeout=ttl)
        return policy
    except Exception as exc:
        logger.exception("Failed to fetch active consent policy → %s", exc)
        return None


def _parse_json_body(request: HttpRequest, max_size: int = 1024 * 1024) -> Dict[str, Any]:
    """Safely parse JSON body with a size limit."""
    try:
        body = request.body or b""
        if len(body) > max_size:
            logger.warning("Request JSON body too large: %d bytes", len(body))
            return {"__error__": "payload_too_large"}
        decoded = body.decode("utf-8") or "{}"
        data = json.loads(decoded)
        if not isinstance(data, dict):
            logger.warning("JSON body is not an object")
            return {}
        return data
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON payload: %s", exc)
        return {}
    except Exception as exc:
        logger.exception("Unexpected error parsing JSON: %s", exc)
        return {}


def _coerce_bool(value: Any) -> bool:
    """Coerce common truthy values to boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in ("1", "true", "yes", "on")


# ============================================================
# Banner Partial
# ============================================================

def banner_partial(request: HttpRequest):
    """Render the consent banner partial."""
    policy = _get_active_policy(request)
    snapshot = getattr(policy, "categories_snapshot", {}) or {}

    derived: Dict[str, bool] = {}
    if isinstance(snapshot, dict):
        for slug, data in snapshot.items():
            derived[slug] = not bool(data.get("required", False))
    else:
        derived = {"functional": True}

    ctx = {
        "consent_active": bool(policy),
        "consent_version": getattr(policy, "version", ""),
        "consent_text": getattr(policy, "banner_text", "We use cookies to improve your experience."),
        "consent_categories": derived,
        "csrf_token": get_token(request),
    }
    return TemplateResponse(request, "consent/includes/banner.html", ctx)


# ============================================================
# Manage Consent Page
# ============================================================

def manage_consent(request: HttpRequest):
    """Render the full consent management page."""
    policy = _get_active_policy(request)
    snapshot = getattr(policy, "categories_snapshot", {}) or {}
    categories = []

    if isinstance(snapshot, dict):
        for slug, data in snapshot.items():
            categories.append({
                "name": data.get("name", slug.title()),
                "slug": slug,
                "description": data.get("description", ""),
                "required": bool(data.get("required", False)),
                "accepted": bool(data.get("default", False)),
            })
    else:
        categories = [
            {"name": "Functional", "slug": "functional", "description": "", "required": True, "accepted": True},
            {"name": "Analytics", "slug": "analytics", "description": "", "required": False, "accepted": False},
            {"name": "Ads", "slug": "ads", "description": "", "required": False, "accepted": False},
        ]

    ctx = {
        "consent_active": bool(policy),
        "consent_version": getattr(policy, "version", ""),
        "consent_text": getattr(policy, "manage_text", "Manage your cookie preferences."),
        "categories": categories,
    }
    return render(request, "site_settings/consent_manage.html", ctx)


# ============================================================
# Consent Status API
# ============================================================

def consent_status(request: HttpRequest):
    """Return the user's current consent state (GET)."""
    policy = _get_active_policy(request)
    if not policy:
        return JsonResponse({"error": "no_active_policy"}, status=404)

    snapshot = getattr(policy, "categories_snapshot", {}) or {}
    categories: Dict[str, Dict[str, Any]] = {}

    for slug, data in snapshot.items():
        categories[slug] = {
            "name": data.get("name", slug.title()),
            "required": bool(data.get("required", False)),
            "default": bool(data.get("default", False)),
            "accepted": bool(data.get("required", False)),  # required defaults to accepted
        }

    if "functional" not in categories:
        categories["functional"] = {"name": "Functional", "required": True, "default": True, "accepted": True}

    site_domain = getattr(get_current_site(request), "domain", None) or request.get_host()

    rec: Optional[ConsentRecord] = None
    if request.user.is_authenticated:
        rec = ConsentRecord.objects.filter(
            user=request.user,
            policy_version=policy.version,
            site_domain=site_domain,
        ).first()
    elif getattr(request, "session", None):
        if not request.session.session_key:
            request.session.create()
        rec = ConsentRecord.objects.filter(
            session_key=request.session.session_key,
            policy_version=policy.version,
            site_domain=site_domain,
        ).first()

    if rec and rec.accepted_categories:
        for slug, val in rec.accepted_categories.items():
            if slug in categories and not categories[slug]["required"]:
                categories[slug]["accepted"] = bool(val)

    return JsonResponse({
        "consent_active": True,
        "consent_version": policy.version,
        "categories": categories,
        "site_domain": site_domain,
    })


# ============================================================
# Consent Accept / Persist
# ============================================================

@require_POST
def consent_accept(request: HttpRequest):
    """
    Accept or reject consent preferences (form or JSON).
    Handles:
      - accept_all / reject_all
      - granular per-slug boolean values
    """
    json_body: Dict[str, Any] = {}
    if (request.content_type or "").startswith("application/json"):
        parsed = _parse_json_body(request)
        if parsed.get("__error__") == "payload_too_large":
            return JsonResponse({"error": "payload_too_large"}, status=413)
        json_body = parsed

    def get_param(key: str, default: Any = None) -> Any:
        return json_body.get(key, request.POST.get(key, default))

    def has_param(key: str) -> bool:
        return key in json_body or key in request.POST

    policy = _get_active_policy(request)
    if not policy:
        return JsonResponse({"ok": False, "error": "no_active_policy"}, status=400)

    snapshot = policy.categories_snapshot or {}
    valid_slugs = set(snapshot.keys()) | {"functional"}
    accepted: Dict[str, bool] = {}

    reject_all = _coerce_bool(get_param("reject_all")) or has_param("reject_all")
    accept_all = _coerce_bool(get_param("accept_all")) or has_param("accept_all")

    if reject_all:
        accepted = {slug: False for slug in valid_slugs}
        accepted["functional"] = True
    elif accept_all:
        accepted = {slug: True for slug in valid_slugs}
    else:
        for slug in valid_slugs:
            if slug == "functional" or snapshot.get(slug, {}).get("required", False):
                accepted[slug] = True
            else:
                accepted[slug] = _coerce_bool(get_param(slug, ""))

    sanitized = {k: bool(v) for k, v in accepted.items() if k in valid_slugs}

    # Ensure session exists for anonymous users
    if getattr(request, "session", None) and not request.session.session_key:
        request.session.create()

    site_domain = getattr(get_current_site(request), "domain", None) or request.get_host()
    defaults = {"accepted_categories": sanitized, "site_domain": site_domain, "session_key": getattr(request.session, "session_key", None)}

    try:
        with transaction.atomic():
            if request.user.is_authenticated:
                ConsentRecord.objects.update_or_create(
                    user=request.user,
                    policy_version=policy.version,
                    site_domain=site_domain,
                    defaults=defaults,
                )
            else:
                ConsentRecord.objects.update_or_create(
                    session_key=request.session.session_key,
                    policy_version=policy.version,
                    site_domain=site_domain,
                    defaults=defaults,
                )
    except Exception as exc:
        logger.exception("Failed to persist ConsentRecord: %s", exc)
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "error": "db_error"}, status=500)
        messages.warning(request, "Unable to save your preferences. They will apply for this session.")
        return redirect(get_param("next") or "/")

    message = "Preferences saved."
    if reject_all:
        message = "You have rejected all optional cookies."
    elif accept_all:
        message = "You have accepted all optional cookies."

    if _is_ajax_request(request):
        return JsonResponse({"ok": True, "message": message, "consent": sanitized})
    messages.success(request, message)
    return redirect(get_param("next") or "/")
