from __future__ import annotations

import urllib.request
from urllib.error import HTTPError, URLError

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Inspect a URL and print status code and headers."

    def add_arguments(self, parser):
        parser.add_argument("url", type=str)

    def handle(self, *args, **options):
        url = options["url"]
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.stdout.write(self.style.SUCCESS(f"{url} -> {resp.getcode()}"))
                for k, v in resp.headers.items():
                    self.stdout.write(f"{k}: {v}")
        except (HTTPError, URLError, Exception) as exc:
            self.stdout.write(self.style.ERROR(f"{url} failed: {exc}"))
