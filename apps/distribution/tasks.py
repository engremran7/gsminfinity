from __future__ import annotations

import logging
from datetime import timedelta

try:
    from celery import shared_task
except Exception:  # pragma: no cover - fallback when Celery not installed

    def shared_task(*dargs, **dkwargs):
        def decorator(func):
            return func

        return decorator


from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.distribution.api import get_settings

from .connectors import dispatch
from .models import ShareJob, SocialAccount

logger = logging.getLogger(__name__)


@shared_task(
    name="distribution.deliver_job",
    bind=True,
    acks_late=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,  # 2 minutes for individual delivery
    time_limit=180,  # 3 minutes hard limit
)
def deliver_job(self, job_id: int) -> None:
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


@shared_task(
    name="distribution.pump_due_jobs",
    bind=True,
    acks_late=True,
    soft_time_limit=60,
    time_limit=90,
)
def pump_due_jobs(self) -> None:
    """Pump due jobs for delivery. Uses values_list for efficiency."""
    now = timezone.now()
    due_ids = list(
        ShareJob.objects.filter(
            status__in=["pending", "queued"], schedule_at__lte=now
        ).values_list("id", flat=True)[:50]
    )
    for job_id in due_ids:
        deliver_job.delay(job_id)


@shared_task(
    name="distribution.retry_failed_jobs",
    bind=True,
    acks_late=True,
    soft_time_limit=60,
    time_limit=90,
)
def retry_failed_jobs(self) -> None:
    cfg = get_settings()
    max_retries = cfg.get("max_retries", 3)
    backoff_seconds = cfg.get("retry_backoff_seconds", 1800)
    cutoff = timezone.now() - timedelta(seconds=backoff_seconds)
    failed = ShareJob.objects.filter(
        status="failed", updated_at__lte=cutoff, attempt_count__lt=max_retries
    )[:50]
    for job in failed:
        job.status = "pending"
        job.save(update_fields=["status", "updated_at"])
        deliver_job.delay(job.id)


def enqueue_pending_for_account(account: SocialAccount) -> int:
    """
    When a social account becomes active, assign and enqueue pending/skipped jobs for that channel.
    Jobs are spaced to respect provider rate limits.
    """
    interval = getattr(settings, "DISTRIBUTION_MIN_ACCOUNT_INTERVAL_SECONDS", 30)
    now = timezone.now()
    jobs = ShareJob.objects.filter(
        channel=account.channel,
        status__in=["pending", "skipped"],
    ).order_by("created_at")[:200]
    count = 0
    for idx, job in enumerate(jobs):
        if not job.account_id:
            job.account = account
        job.status = "pending"
        if not job.schedule_at:
            job.schedule_at = now + timedelta(seconds=interval * idx)
        job.save(update_fields=["account", "status", "schedule_at", "updated_at"])
        deliver_job.delay(job.id)
        count += 1
    return count
