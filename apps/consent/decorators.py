# apps/consent/decorators.py
"""
Consent Decorators
------------------
Reusable decorators to enforce consent validation for
protected or analytics-sensitive endpoints.

Features:
- Sync & async view support (Django 4.2+)
- Works with middleware-injected cookie_consent namespace
- AJAX-friendly JSON response
- Graceful fallback when middleware missing
"""

import asyncio
import logging
from functools import wraps
from inspect import iscoroutinefunction

from django.http import HttpResponseForbidden, JsonResponse

log = logging.getLogger(__name__)


def require_consent(category: str = "analytics", ajax_friendly: bool = True):
    """
    Decorator to enforce cookie/data-usage consent before executing a view.

    Args:
        category (str): Consent category slug (e.g., "analytics", "ads", "functional").
        ajax_friendly (bool): If True, returns JSON 403 for AJAX requests.

    Behavior:
        ✅ Checks `request.cookie_consent` and `request.has_cookie_consent`
        ✅ Graceful fallback when middleware not initialized
        ✅ Works with both sync and async Django views
        ✅ Prevents accidental access without consent
    """

    def _deny_access(request, category: str):
        """Return a standardized 403 response."""
        msg = f"Consent required for category '{category}'."
        if ajax_friendly and (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or (request.content_type or "").startswith("application/json")
        ):
            return JsonResponse(
                {"error": "consent_required", "category": category}, status=403
            )
        return HttpResponseForbidden(msg, content_type="text/plain; charset=utf-8")

    def decorator(view_func):
        if iscoroutinefunction(view_func):
            # ---------------- Async Path ----------------
            @wraps(view_func)
            async def _wrapped_async(request, *args, **kwargs):
                try:
                    cookie_ns = getattr(request, "cookie_consent", None)
                    has_category = (
                        bool(getattr(cookie_ns, category, False))
                        if cookie_ns
                        else False
                    )
                    has_overall = bool(getattr(request, "has_cookie_consent", False))

                    if not (has_category and has_overall):
                        log.info(
                            "Access blocked (async): user=%s ip=%s category=%s path=%s",
                            getattr(request.user, "email", "anon"),
                            request.META.get("REMOTE_ADDR", "unknown"),
                            category,
                            request.path,
                        )
                        return _deny_access(request, category)
                except Exception as exc:
                    log.warning(
                        "Consent validation failed (async) for %s → %s", category, exc
                    )
                    return HttpResponseForbidden("Consent validation error.")
                return await view_func(request, *args, **kwargs)

            return _wrapped_async

        # ---------------- Sync Path ----------------
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            try:
                cookie_ns = getattr(request, "cookie_consent", None)
                has_category = (
                    bool(getattr(cookie_ns, category, False)) if cookie_ns else False
                )
                has_overall = bool(getattr(request, "has_cookie_consent", False))

                if not (has_category and has_overall):
                    log.info(
                        "Access blocked: user=%s ip=%s category=%s path=%s",
                        getattr(request.user, "email", "anon"),
                        request.META.get("REMOTE_ADDR", "unknown"),
                        category,
                        request.path,
                    )
                    return _deny_access(request, category)
            except Exception as exc:
                log.warning("Consent validation failed for %s → %s", category, exc)
                return HttpResponseForbidden("Consent validation error.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator