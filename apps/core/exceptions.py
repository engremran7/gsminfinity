"""
Custom exception handlers for uniform JSON + HTML safety.
"""

import logging
from django.http import JsonResponse
from django.conf import settings

log = logging.getLogger(__name__)

def json_error_response(exc, code=500):
    data = {"ok": False, "error": str(exc), "type": exc.__class__.__name__}
    if not settings.DEBUG:
        data["error"] = "Internal server error"
    return JsonResponse(data, status=code)
