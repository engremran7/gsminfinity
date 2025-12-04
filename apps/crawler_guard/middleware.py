
from __future__ import annotations

import fnmatch
import hashlib
from typing import Callable, Optional

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse

from apps.core.app_service import AppService
from apps.core.models import AppRegistry
from apps.core.utils.ip import get_client_ip
from apps.crawler_guard.models import CrawlerEvent, CrawlerRule


class CrawlerGuardMiddleware:
    """
    Lightweight anti-scraping middleware. Uses AppRegistry toggle and dynamic devices API.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        # Skip if disabled in registry
        try:
            reg = AppRegistry.get_solo()
            if not getattr(reg, "crawler_guard_enabled", True):
                return self.get_response(request)
        except Exception:
            pass

        rule = self._match_rule(request.path_info)
        ip = get_client_ip(request) or ""
        device_id = self._resolve_device_identifier(request)
        headers_hash = self._hash_headers(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        response: Optional[HttpResponse] = None
        action_taken = "allow"

        is_known_bot = any(
            b in (user_agent or "").lower() for b in ["googlebot", "bingbot", "duckduckbot", "slurp"]
        )

        if rule:
            action_taken = rule.action
            over_limit = self._over_limit(rule, ip, device_id, headers_hash)
            if rule.action == "block" and not is_known_bot:
                response = HttpResponseForbidden("Request blocked.")
            elif rule.action == "throttle":
                if over_limit and not is_known_bot:
                    response = JsonResponse({"detail": "Too many requests."}, status=429)
                else:
                    action_taken = "allow"
            elif rule.action == "challenge" and not is_known_bot:
                # Primitive challenge placeholder; integrate captcha/turnstile provider here.
                response = JsonResponse(
                    {"detail": "Challenge required", "challenge": "turnstile"},
                    status=429,
                )
                response["X-Crawler-Challenge"] = "required"
            else:
                action_taken = "allow"

        self._log_event(
            ip=ip,
            device_identifier=device_id,
            path=request.path_info,
            rule=rule,
            action_taken=action_taken,
            user_agent=user_agent,
            headers_hash=headers_hash,
        )

        if response:
            return response

        return self.get_response(request)

    def _match_rule(self, path: str) -> Optional[CrawlerRule]:
        try:
            rules = CrawlerRule.objects.filter(is_enabled=True).order_by("-priority")
            for rule in rules:
                if fnmatch.fnmatch(path, rule.path_pattern):
                    return rule
        except Exception:
            return None
        return None

    def _resolve_device_identifier(self, request) -> Optional[str]:
        """
        Best-effort device identifier using devices API if enabled.
        """
        try:
            devices_api = AppService.get("devices")
            if devices_api and hasattr(devices_api, "resolve_identity"):
                ident = devices_api.resolve_identity(request)
                return ident.get("machine_uuid") or ident.get("server_fallback_fp")
        except Exception:
            return None
        return None

    def _hash_headers(self, request) -> str:
        headers = []
        for k, v in request.META.items():
            if k.startswith("HTTP_"):
                # Skip sensitive headers to avoid logging secrets
                if k in {"HTTP_AUTHORIZATION", "HTTP_COOKIE"}:
                    continue
                headers.append(f"{k}:{v}")
        data = "|".join(sorted(headers)).encode("utf-8", errors="ignore")
        return hashlib.sha256(data).hexdigest()

    def _log_event(
        self,
        *,
        ip: str,
        device_identifier: Optional[str],
        path: str,
        rule: Optional[CrawlerRule],
        action_taken: str,
        user_agent: str,
        headers_hash: str,
    ) -> None:
        try:
            CrawlerEvent.objects.create(
                ip=ip,
                device_identifier=device_identifier,
                path=path,
                rule_triggered=rule,
                action_taken=action_taken,
                user_agent=user_agent,
                headers_hash=headers_hash,
                metadata={
                    "rule_id": getattr(rule, "id", None),
                    "priority": getattr(rule, "priority", None),
                    "stop_processing": getattr(rule, "stop_processing", None),
                },
            )
        except Exception:
            # Fail-open without blocking request
            pass

    def _over_limit(self, rule: CrawlerRule, ip: str, device_identifier: Optional[str], headers_hash: str) -> bool:
        if not rule.requests_per_minute:
            return False
        keys = [f"cg:{rule.id}:ip:{ip}"]
        if device_identifier:
            keys.append(f"cg:{rule.id}:dev:{device_identifier}")
        if headers_hash:
            keys.append(f"cg:{rule.id}:hdr:{headers_hash}")
        for key in keys:
            try:
                current = cache.incr(key)
                if current == 1:
                    cache.expire(key, 60)
            except Exception:
                try:
                    val = cache.get(key, 0) + 1
                    cache.set(key, val, 60)
                    current = val
                except Exception:
                    continue
            if current > rule.requests_per_minute:
                return True
        return False


