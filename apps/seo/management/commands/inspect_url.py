from __future__ import annotations

import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.seo.views import _is_private_host, _NoRedirect


class Command(BaseCommand):
    help = "Inspect a URL and print status code and headers."

    def add_arguments(self, parser):
        parser.add_argument("url", type=str)

    def handle(self, *args, **options):
        url = options["url"]
        allowed_hosts = getattr(settings, "SEO_INSPECT_ALLOWLIST", ())
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            self.stdout.write(self.style.ERROR(f"{url} failed: invalid_url"))
            return
        if allowed_hosts and parsed.hostname not in allowed_hosts:
            self.stdout.write(self.style.ERROR(f"{url} failed: forbidden_target"))
            return
        if _is_private_host(parsed.hostname):
            self.stdout.write(self.style.ERROR(f"{url} failed: forbidden_target"))
            return
        try:
            req = urllib.request.Request(url, method="HEAD")
            opener = urllib.request.build_opener(_NoRedirect)
            with opener.open(req, timeout=5) as resp:
                self.stdout.write(self.style.SUCCESS(f"{url} -> {resp.getcode()}"))
                for k, v in resp.headers.items():
                    self.stdout.write(f"{k}: {v}")
        except (HTTPError, URLError, Exception) as exc:
            self.stdout.write(self.style.ERROR(f"{url} failed: {exc}"))
