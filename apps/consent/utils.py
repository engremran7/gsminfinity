from __future__ import annotations

import hashlib
import os

from django.conf import settings

CONSENT_SALT = os.environ.get(
    "CONSENT_HASH_SALT", getattr(settings, "CONSENT_HASH_SALT", "gsm-default-salt")
).encode(
    "utf-8",
    "ignore",
)


def check(scope: str, request) -> bool:
    """
    Central consent gate. Returns True if the given scope is permitted.
    Scopes: "ads", "analytics", "personalization".
    Defaults to False when consent state is missing/unknown (opt-in).
    """
    # Prefer middleware-attached categories map.
    state = getattr(request, "consent_categories", None)
    if not state:
        state = getattr(request, "consent_context", None) or getattr(
            request, "consent_state", None
        )
    if not state:
        return False

    scope_val: bool | None = None
    if isinstance(state, dict):
        scope_val = state.get(f"{scope}_enabled")
        if scope_val is None:
            scope_val = state.get(scope)
    else:
        scope_val = getattr(state, f"{scope}_enabled", None)
        if scope_val is None:
            scope_val = getattr(state, scope, None)

    if scope_val is False or scope_val is None:
        return False
    return True


def get_active_policy(domain: str = ""):
    """
    Resolve the active ConsentPolicy model (if any).
    Returns the model instance to avoid breaking admin/rendering; callers should
    handle serialization as needed.
    """
    try:
        from apps.consent.models import ConsentPolicy

        qs = ConsentPolicy.objects.filter(is_active=True)
        if domain:
            qs = qs.filter(site_domain__iexact=domain)
        return qs.order_by("-effective_from").first()
    except Exception:
        return None


def serialize_policy(policy) -> dict | None:
    if not policy:
        return None
    try:
        return {
            "version": getattr(policy, "version", None),
            "site_domain": getattr(policy, "site_domain", ""),
            "categories_snapshot": getattr(policy, "categories_snapshot", {}) or {},
            "banner_text": getattr(policy, "banner_text", ""),
            "manage_text": getattr(policy, "manage_text", ""),
            "public_slug": getattr(policy, "public_slug", ""),
            "public_url": getattr(policy, "public_url", ""),
        }
    except Exception:
        return None


def resolve_policy_url(policy, default_slug: str = "privacy") -> str:
    """
    Resolve the public URL for a policy:
    1) explicit policy.public_url if set
    2) pages app route using public_slug or default_slug if available
    3) fallback to consent privacy center
    """
    if not policy:
        return ""
    if getattr(policy, "public_url", ""):
        return policy.public_url
    slug = getattr(policy, "public_slug", "") or default_slug
    # Try pages app
    try:
        from django.urls import reverse

        return reverse("pages:page", kwargs={"slug": slug})
    except Exception:
        pass
    # Fallback to consent privacy center
    try:
        from django.urls import reverse

        return reverse("consent:privacy_center")
    except Exception:
        return ""


def consent_cache_key(domain: str = "") -> str:
    return f"consent_policy::{domain or 'default'}"


def resolve_site_domain(request) -> str:
    return (
        getattr(request, "site_domain", "") or request.get_host()
        if hasattr(request, "get_host")
        else ""
    )


def hash_ip(ip: str) -> str:
    payload = CONSENT_SALT + (ip or "").encode("utf-8", "ignore")
    return hashlib.sha256(payload).hexdigest()


def hash_ua(ua: str) -> str:
    payload = CONSENT_SALT + (ua or "").encode("utf-8", "ignore")
    return hashlib.sha256(payload).hexdigest()


def consent_cookie_settings() -> tuple[str, dict]:
    """
    Returns (cookie_name, options) so views/middleware share the same policy.
    """
    name = getattr(settings, "CONSENT_COOKIE_NAME", "consent_status")
    opts = {
        "max_age": int(getattr(settings, "CONSENT_COOKIE_MAX_AGE", 60 * 60 * 24 * 365)),
        "samesite": getattr(settings, "CONSENT_COOKIE_SAMESITE", "Lax"),
        "secure": bool(getattr(settings, "CONSENT_COOKIE_SECURE", not settings.DEBUG)),
        "httponly": False,  # UI needs read access
        "path": "/",
    }
    domain = getattr(settings, "CONSENT_COOKIE_DOMAIN", "")
    if domain:
        opts["domain"] = domain
    return name, opts


def set_consent_cookie(response, value) -> None:
    """
    Helper to set the consent cookie using unified settings.
    Value is JSON-encoded when passed a dict; other values stringified.
    """
    name, opts = consent_cookie_settings()
    try:
        if isinstance(value, dict):
            import json

            value = json.dumps(value)
        response.set_cookie(name, value, **opts)
    except Exception:
        # Defensive: avoid breaking the response path
        pass
