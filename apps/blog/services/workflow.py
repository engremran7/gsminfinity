from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.blog.models import Post, PostStatus


class WorkflowAction(enum.Enum):
    REQUEST_REVIEW = "request_review"
    PUBLISH = "publish"
    SCHEDULE = "schedule"
    ARCHIVE = "archive"


@dataclass
class WorkflowResult:
    ok: bool
    status: str
    message: str = ""


def request_review(post: Post, user=None) -> WorkflowResult:
    with transaction.atomic():
        post.status = PostStatus.IN_REVIEW
        post.save(update_fields=["status", "updated_at"])
    return WorkflowResult(ok=True, status=post.status, message="Moved to review")


def schedule(post: Post, when: datetime, user=None) -> WorkflowResult:
    when = when or timezone.now()
    with transaction.atomic():
        post.status = PostStatus.SCHEDULED
        post.publish_at = when
        post.save(update_fields=["status", "publish_at", "updated_at"])
    return WorkflowResult(ok=True, status=post.status, message="Scheduled")


def publish(post: Post, user=None) -> WorkflowResult:
    now = timezone.now()
    with transaction.atomic():
        post.status = PostStatus.PUBLISHED
        post.publish_at = post.publish_at or now
        post.published_at = post.published_at or now
        post.save(update_fields=["status", "publish_at", "published_at", "updated_at"])
    return WorkflowResult(ok=True, status=post.status, message="Published")


def archive(post: Post, user=None) -> WorkflowResult:
    with transaction.atomic():
        post.status = PostStatus.ARCHIVED
        post.save(update_fields=["status", "updated_at"])
    return WorkflowResult(ok=True, status=post.status, message="Archived")
