"""
apps.core.exceptions
====================

Enterprise-grade unified exception handling.

✓ Django 5.2 / Python 3.12+
✓ Async-safe, JSON + HTML aware
✓ Hardened against info disclosure
✓ DRF-compatible (wired via REST_FRAMEWORK.EXCEPTION_HANDLER)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.conf import settings
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
    ObjectDoesNotExist,
)
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.utils.translation import gettext_lazy as _

# -------------------------------------------------------------
# Optional DRF imports — explicit, safe, no broad try/except
# -------------------------------------------------------------
AuthenticationFailed = None
APIException = None

try:
    from rest_framework.exceptions import AuthenticationFailed as _AuthFailed
    from rest_framework.exceptions import APIException as _APIException
    AuthenticationFailed = _AuthFailed
    APIException = _APIException
except ImportError:
    # DRF not installed — these remain None (safe)
    pass

log = logging.getLogger(__name__)


# ============================================================
#  Utility helpers
# ============================================================
def _is_json_request(request: Optional[HttpRequest]) -> bool:
    """Detect JSON or AJAX requests for correct response type."""
    if not request:
        return False

    content_type = (request.content_type or "").lower()

    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or content_type.startswith("application/json")
        or content_type.endswith("+json")
    )


def json_error_response(
    exc: Exception,
    code: int = 500,
    request: Optional[HttpRequest] = None,
) -> JsonResponse:
    """
    Hardened JSON error response.
    Internal exception details are hidden when DEBUG=False.
    """
    message = str(exc) if settings.DEBUG else _("Internal server error")

    return JsonResponse(
        {
            "ok": False,
            "error": message,
            "type": exc.__class__.__name__,
            "status": code,
        },
        status=code,
        json_dumps_params={"ensure_ascii": False},
    )


# ============================================================
#  Django / DRF unified exception handler
# ============================================================
class EnterpriseExceptionHandler:
    """
    Centralized handler for Django + DRF errors.

    Enable using:

        REST_FRAMEWORK = {
            "EXCEPTION_HANDLER": "apps.core.exceptions.EnterpriseExceptionHandler.handle_api_exception"
        }
    """

    @staticmethod
    def handle_api_exception(
        exc: Exception,
        context: Optional[dict[str, Any]] = None,
    ) -> JsonResponse:
        request = context.get("request") if context else None
        status_code: int
        response_data: dict[str, Any]

        # ------------------------------------------
        # Authentication / Permissions
        # ------------------------------------------
        if isinstance(exc, (PermissionDenied, AuthenticationFailed)):
            status_code = 401
            response_data = {
                "ok": False,
                "error": "authentication_failed",
                "message": _("Invalid credentials or insufficient permissions."),
            }

        # ------------------------------------------
        # Validation
        # ------------------------------------------
        elif isinstance(exc, ValidationError):
            status_code = 400
            details = getattr(exc, "message_dict", None) or str(exc)
            response_data = {
                "ok": False,
                "error": "validation_failed",
                "details": details,
            }

        # ------------------------------------------
        # Missing objects
        # ------------------------------------------
        elif isinstance(exc, ObjectDoesNotExist):
            status_code = 404
            response_data = {
                "ok": False,
                "error": "not_found",
                "message": _("Requested resource was not found."),
            }

        # ------------------------------------------
        # DRF base exceptions (ParseError, NotAuthenticated, etc.)
        # ------------------------------------------
        elif APIException and isinstance(exc, APIException):
            status_code = getattr(exc, "status_code", 500)
            response_data = {
                "ok": False,
                "error": getattr(exc, "default_code", "api_exception"),
                "message": str(getattr(exc, "detail", exc)),
            }

        # ------------------------------------------
        # Unhandled error (safe fallback)
        # ------------------------------------------
        else:
            log.exception("Unhandled exception occurred", exc_info=True)
            status_code = 500
            response_data = {
                "ok": False,
                "error": "internal_error",
                "message": (
                    f"{exc.__class__.__name__}: {exc}"
                    if settings.DEBUG
                    else _("An unexpected error occurred.")
                ),
            }

        return JsonResponse(
            response_data,
            status=status_code,
            json_dumps_params={
                "ensure_ascii": False,
                "indent": 2 if settings.DEBUG else None,
            },
        )


# ============================================================
#  Synchronous Django view fallback (non-DRF)
# ============================================================
def handle_view_exception(
    request: HttpRequest,
    exc: Exception,
    code: int = 500,
) -> HttpResponse:
    """
    Generic handler for standard Django views.
    Returns JSON for AJAX/JSON requests; otherwise text/plain.
    """
    # Only include traceback info when DEBUG=True (safe)
    log.warning("View exception caught: %s", exc, exc_info=settings.DEBUG)

    if _is_json_request(request):
        return json_error_response(exc, code=code, request=request)

    message = (
        f"{exc.__class__.__name__}: {exc}"
        if settings.DEBUG
        else _("Internal server error")
    )

    return HttpResponse(
        message,
        status=code,
        content_type="text/plain; charset=utf-8",
    )
