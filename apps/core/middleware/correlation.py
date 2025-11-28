import logging
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware:
    """
    Adds a per-request correlation ID for traceability across logs.
    """

    header_name = "X-Request-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = (
            request.META.get(self.header_name.replace("-", "_").upper())
            or str(uuid.uuid4())
        )
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response[self.header_name] = correlation_id
        return response
