from __future__ import annotations

import urllib.request
from urllib.error import URLError, HTTPError

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.seo.models import SitemapEntry


class Command(BaseCommand):
    help = "Checks active sitemap entries for HTTP reachability."

    def handle(self, *args, **options):
        entries = SitemapEntry.objects.filter(is_active=True)
        ok = 0
        bad = 0
        for entry in entries:
            try:
                req = urllib.request.Request(entry.url, method="HEAD")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    code = resp.getcode()
                    entry.last_status = code
                    entry.last_checked_at = timezone.now()
                    entry.save(update_fields=["last_status", "last_checked_at"])
                    if 200 <= code < 400:
                        ok += 1
                        continue
                bad += 1
            except (HTTPError, URLError, Exception):
                entry.last_status = 0
                entry.last_checked_at = timezone.now()
                entry.save(update_fields=["last_status", "last_checked_at"])
                bad += 1
        self.stdout.write(self.style.SUCCESS(f"Checked {entries.count()} URLs. OK: {ok}, Bad: {bad}"))
