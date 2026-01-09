from __future__ import annotations

from collections.abc import Iterable
from functools import wraps

from django.http import HttpResponseForbidden

from apps.consent.utils import check as consent_check


def consent_required(scopes: Iterable[str]):
    """
    Decorator to enforce consent scopes on views.
    Usage:
        @consent_required(["functional", "comments"])
        def my_view(request, ...):
            ...
    """

    required = list(scopes or [])

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            for scope in required:
                if not consent_check(scope, request):
                    return HttpResponseForbidden(f"Consent required: {scope}")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
