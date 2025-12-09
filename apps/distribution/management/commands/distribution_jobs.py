from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.distribution.api import get_settings
from apps.distribution.models import ShareJob
from apps.distribution.tasks import deliver_job
from django.db import models


class Command(BaseCommand):
    help = "Inspect and control distribution jobs (retry, cancel, requeue, stats)."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        retry = subparsers.add_parser("retry", help="Retry failed jobs or a specific id")
        retry.add_argument("--id", type=int, help="Specific job id")
        retry.add_argument("--status", default="failed", help="Status to retry (default=failed)")
        retry.add_argument("--limit", type=int, default=50, help="Max jobs to retry")

        cancel = subparsers.add_parser("cancel", help="Cancel a job by id")
        cancel.add_argument("--id", type=int, required=True)

        requeue = subparsers.add_parser("requeue", help="Requeue pending/queued jobs")
        requeue.add_argument("--status", default="pending", help="Status to requeue (pending/queued)")
        requeue.add_argument("--limit", type=int, default=50)

        stats = subparsers.add_parser("stats", help="Show job counts by status")
        stats.add_argument("--channel", help="Filter by channel")

    def handle(self, *args, **options):
        action = options["action"]
        if action == "retry":
            return self._retry(options)
        if action == "cancel":
            return self._cancel(options)
        if action == "requeue":
            return self._requeue(options)
        if action == "stats":
            return self._stats(options)
        raise CommandError(f"Unknown action {action}")

    def _retry(self, opts):
        job_id = opts.get("id")
        status = opts.get("status") or "failed"
        limit = opts.get("limit") or 50
        qs = ShareJob.objects.filter(status=status)
        cfg = get_settings()
        max_retries = cfg.get("max_retries", 3)
        if job_id:
            qs = qs.filter(pk=job_id)
        qs = qs.filter(attempt_count__lt=max_retries).order_by("updated_at")[:limit]
        count = qs.count()
        for job in qs:
            job.status = "pending"
            job.save(update_fields=["status", "updated_at"])
            deliver_job.delay(job.id)
        self.stdout.write(self.style.SUCCESS(f"Queued retries for {count} job(s)."))

    def _cancel(self, opts):
        job_id = opts.get("id")
        if not job_id:
            raise CommandError("--id is required for cancel")
        try:
            job = ShareJob.objects.get(pk=job_id)
        except ShareJob.DoesNotExist:
            raise CommandError(f"Job {job_id} not found")
        job.status = "cancelled"
        job.save(update_fields=["status", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Cancelled job {job_id}."))

    def _requeue(self, opts):
        status = opts.get("status") or "pending"
        limit = opts.get("limit") or 50
        qs = ShareJob.objects.filter(status=status).order_by("updated_at")[:limit]
        count = qs.count()
        for job in qs:
            job.status = "pending"
            job.save(update_fields=["status", "updated_at"])
            deliver_job.delay(job.id)
        self.stdout.write(self.style.SUCCESS(f"Requeued {count} job(s)."))

    def _stats(self, opts):
        channel = opts.get("channel")
        qs = ShareJob.objects.all()
        if channel:
            qs = qs.filter(channel=channel)
        counts = qs.values_list("status").order_by().annotate(count=models.Count("id"))
        for status, count in counts:
            self.stdout.write(f"{status}: {count}")
        total = qs.count()
        self.stdout.write(f"Total: {total}")
