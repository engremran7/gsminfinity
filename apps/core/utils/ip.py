
from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """
    Centralized, proxy-aware client IP resolution.

    - Honors TRUSTED_PROXY_COUNT to peel trusted proxies from X-Forwarded-For.
    - Falls back to X-Real-IP then REMOTE_ADDR.
    - Never raises; returns empty string if unknown.
    """
    try:
        trusted_hops = int(getattr(settings, "TRUSTED_PROXY_COUNT", 0) or 0)
    except (TypeError, ValueError):
        trusted_hops = 0

    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff and trusted_hops > 0:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if len(parts) >= trusted_hops + 1:
            return parts[-(trusted_hops + 1)]

    real_ip = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real_ip:
        return real_ip

    return request.META.get("REMOTE_ADDR", "") or ""


