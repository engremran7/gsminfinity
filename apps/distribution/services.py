
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core import ai_client
from apps.core.utils.logging import log_event
from apps.blog.models import Post, PostStatus
from apps.core.app_service import AppService
from .models import (
    Channel,
    ContentVariant,
    ShareJob,
    SharePlan,
    ShareTemplate,
    SocialAccount,
)

logger = logging.getLogger(__name__)


def _enabled_channels() -> List[str]:
    try:
        dist_api = AppService.get("distribution")
        settings_obj = dist_api.get_settings() if dist_api and hasattr(dist_api, "get_settings") else {}
        if not settings_obj.get("distribution_enabled", True):
            return []
    except Exception:
        pass
    return getattr(settings, "DISTRIBUTION_CHANNELS", list(Channel.values))


def _default_template(channel: str) -> ShareTemplate | None:
    tmpl = (
        ShareTemplate.objects.filter(channel=channel, is_default=True).first()
        or ShareTemplate.objects.filter(channel=channel).first()
    )
    return tmpl


def _ensure_variants(post: Post, channels: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    variants: Dict[str, Dict[str, Any]] = {}
    for ch in channels:
        try:
            summary = (
                ai_client.summarize_text(post.summary or post.body, None)
                if hasattr(ai_client, "summarize_text")
                else post.summary
            )
        except Exception:
            summary = post.summary
        try:
            title = (
                ai_client.generate_title(post.title, None)
                if hasattr(ai_client, "generate_title")
                else post.title
            )
        except Exception:
            title = post.title
        try:
            hashtags = (
                ai_client.generate_tags(post.summary or post.body, None)
                if hasattr(ai_client, "generate_tags")
                else []
            )
        except Exception:
            hashtags = []
        variant_payload = {
            "title": title or post.title,
            "summary": summary or post.summary,
            "hashtags": hashtags or [],
            "url": post.get_absolute_url(),
        }
        variants[ch] = variant_payload
        ContentVariant.objects.update_or_create(
            post=post,
            channel=ch,
            variant_type="summary",
            defaults={"payload": variant_payload},
        )
    return variants


def _absolute_url(url: str) -> str:
    """
    Guarantee an absolute URL for downstream channels (indexing/social).
    """
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = getattr(settings, "SITE_URL", "").rstrip("/")
    return f"{base}{url}" if base else url


def _build_payload(post: Post, channel: str, template: ShareTemplate | None, variants: Dict[str, Any]) -> Dict[str, Any]:
    data = variants.get(channel) or {}
    tmpl = template.body_template if template else "{title} {url}"
    url = data.get("url") or post.get_absolute_url()
    body = tmpl.format(
        title=data.get("title") or post.title,
        url=_absolute_url(url),
        summary=data.get("summary") or post.summary,
        hashtags=" ".join(f"#{h}" for h in data.get("hashtags", [])[:6]),
    )
    payload = {"body": body}
    if template and template.media_template:
        payload["media"] = template.media_template
    return payload


@transaction.atomic
def create_plan_for_post(post: Post, *, channels: Iterable[str] | None = None, schedule_at=None, created_by=None) -> SharePlan:
    channels = list(channels or _enabled_channels())
    if not channels:
        return None
    existing = SharePlan.objects.filter(
        post=post, status__in=["pending", "queued", "sent"]
    ).first()
    if existing:
        return existing
    plan = SharePlan.objects.create(
        post=post,
        channels=channels,
        schedule_at=schedule_at,
        status="queued" if schedule_at and schedule_at > timezone.now() else "pending",
        created_by=created_by,
    )
    variants = _ensure_variants(post, channels)
    jobs: List[ShareJob] = []
    for ch in channels:
        template = _default_template(ch)
        payload = _build_payload(post, ch, template, variants)
        account = (
            SocialAccount.objects.filter(channel=ch, is_active=True).first()
            if ch not in {Channel.RSS, Channel.ATOM, Channel.JSON, Channel.WEBSUB}
            else None
        )
        jobs.append(
            ShareJob(
                post=post,
                plan=plan,
                account=account,
                channel=ch,
                payload=payload,
                schedule_at=schedule_at,
                status="pending",
            )
        )
    ShareJob.objects.bulk_create(jobs)
    return plan


def should_fanout(post: Post) -> bool:
    return post.status == PostStatus.PUBLISHED and post.publish_at and post.publish_at <= timezone.now()


def fanout_post_publish(post: Post, *, created_by=None) -> SharePlan | None:
    if not should_fanout(post):
        return None
    plan = create_plan_for_post(post, created_by=created_by)
    if not plan:
        logger.info("distribution.plan.skipped", extra={"post": post.slug, "reason": "no_channels"})
        return None
    log_event(logger, "info", "distribution.plan.created", post=post.slug, plan=plan.id, channels=plan.channels)
    return plan


