
from __future__ import annotations

import os
from datetime import timedelta
import logging

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("app")
app.config_from_object("django.conf:settings", namespace="CELERY")

# =============================================================================
# ENTERPRISE TASK DEFAULTS
# =============================================================================
# Default timeouts for all tasks (can be overridden per-task)
DEFAULT_SOFT_TIME_LIMIT = 300  # 5 minutes - task gets SoftTimeLimitExceeded
DEFAULT_TIME_LIMIT = 600       # 10 minutes - task is killed (SIGTERM)
DEFAULT_MAX_RETRIES = 3        # Number of retry attempts
DEFAULT_RETRY_DELAY = 60       # Seconds between retries

app.conf.update(
    task_default_queue="default",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Enterprise reliability settings
    task_acks_late=True,              # Acknowledge after completion (survive worker crash)
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    worker_prefetch_multiplier=1,     # Fair task distribution
    task_track_started=True,          # Track task state transitions
    # Default timeouts for all tasks
    task_soft_time_limit=DEFAULT_SOFT_TIME_LIMIT,
    task_time_limit=DEFAULT_TIME_LIMIT,
    task_default_exchange="celery",
    task_default_routing_key="celery",
)

# Dead Letter Queue configuration (requires RabbitMQ broker arguments)
# Failed tasks after max_retries are routed here for manual inspection
app.conf.task_queues = {
    "default": {
        "exchange": "celery",
        "routing_key": "celery",
    },
    "dlq": {
        "exchange": "dlq",
        "routing_key": "dlq",
    },
}

# Error handling hook to route failed tasks to DLQ
@app.task(bind=True, name="celery.failure_handler")
def failure_handler(self, task_id, exception, traceback, einfo, args, kwargs):
    """Route permanently failed tasks to DLQ for inspection."""
    logger = logging.getLogger(__name__)
    logger.error(
        f"Task {task_id} permanently failed: {exception}",
        extra={"task_id": task_id, "args": args, "kwargs": kwargs}
    )

# Periodic automation for distribution subsystem
app.conf.beat_schedule = {
    "distribution-pump-due-jobs": {
        "task": "distribution.pump_due_jobs",
        "schedule": timedelta(seconds=60),
    },
    "distribution-retry-failed": {
        "task": "distribution.retry_failed_jobs",
        "schedule": timedelta(minutes=5),
    },
}

app.autodiscover_tasks()


@app.task(name="health.ping")
def health_ping():
    """Lightweight worker ping task."""
    return {"ok": True}


# debug_task removed to avoid shipping dev/demo tasks in production


