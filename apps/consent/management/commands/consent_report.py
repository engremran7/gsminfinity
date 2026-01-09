from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.consent.models import ConsentDecision


class Command(BaseCommand):
    help = "Generate a simple consent report (accepts per category today)."

    def handle(self, *args, **options):
        today = timezone.now().date()
        decisions = ConsentDecision.objects.filter(created_at__date=today)
        category_counts = {}
        for d in decisions:
            cats = d.categories or {}
            for k, v in cats.items():
                if v:
                    category_counts[k] = category_counts.get(k, 0) + 1
        self.stdout.write(f"Consent report for {today}:")
        for k, v in category_counts.items():
            self.stdout.write(f"  {k}: {v}")
