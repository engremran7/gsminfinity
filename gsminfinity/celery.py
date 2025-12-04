
from __future__ import annotations

import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gsminfinity.settings")

app = Celery("gsminfinity")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Sensible enterprise defaults; can be overridden via settings.py
app.conf.update(
    task_default_queue="default",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
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


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


