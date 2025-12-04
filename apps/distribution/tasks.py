
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from django.db import transaction

from .connectors import dispatch
from .models import ShareJob

logger = logging.getLogger(__name__)


@shared_task(name="distribution.deliver_job")
def deliver_job(job_id: int) -> None:
    try:
        with transaction.atomic():
            job = (
                ShareJob.objects.select_for_update(skip_locked=True)
                .select_related("post")
                .get(pk=job_id)
            )
            if job.status not in {"pending", "queued"}:
                return
            job.attempt_count += 1
            job.status = "queued"
            job.save(update_fields=["status", "attempt_count", "updated_at"])
    except ShareJob.DoesNotExist:  # pragma: no cover - defensive
        return

    result = dispatch(job)
    job.status = result.status_override or ("sent" if result.ok else "failed")
    job.last_error = "" if result.ok else result.message
    job.external_post_id = result.external_id or ""
    job.save(update_fields=["status", "last_error", "external_post_id", "updated_at"])


@shared_task(name="distribution.pump_due_jobs")
def pump_due_jobs() -> None:
    now = timezone.now()
    due = ShareJob.objects.filter(status__in=["pending", "queued"], schedule_at__lte=now)[:50]
    for job in due:
        deliver_job.delay(job.id)


@shared_task(name="distribution.retry_failed_jobs")
def retry_failed_jobs() -> None:
    cutoff = timezone.now() - timedelta(hours=6)
    failed = ShareJob.objects.filter(status="failed", updated_at__gte=cutoff, attempt_count__lt=3)[:50]
    for job in failed:
        job.status = "pending"
        job.save(update_fields=["status", "updated_at"])
        deliver_job.delay(job.id)


