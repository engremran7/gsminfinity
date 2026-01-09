from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from apps.distribution.api import get_settings
from apps.distribution.models import ShareJob, ShareLog, SocialAccount

logger = logging.getLogger(__name__)


@dataclass
class ConnectorResult:
    ok: bool
    message: str = ""
    external_id: str | None = None
    response_code: str | None = None
    status_override: str | None = None


class Connector(Protocol):
    channel: str

    def send(self, job: ShareJob) -> ConnectorResult: ...


def _log(job: ShareJob, result: ConnectorResult) -> None:
    ShareLog.objects.create(
        job=job,
        level="info" if result.ok else "error",
        message=result.message[:500],
        response_code=result.response_code or "",
        metadata={"external_id": result.external_id},
    )


class StubConnector:
    """
    Safe placeholder that marks jobs as skipped with a descriptive message.
    """

    channel: str = "stub"

    def send(self, job: ShareJob) -> ConnectorResult:  # pragma: no cover - thin wrapper
        return ConnectorResult(
            ok=False, message=f"Connector not implemented for {job.channel}"
        )


class LoggingConnector(StubConnector):
    """
    No-op connector that logs payloads. Useful in dev/mock mode.
    """

    def send(self, job: ShareJob) -> ConnectorResult:
        logger.debug("LoggingConnector %s payload=%s", job.channel, job.payload)
        return ConnectorResult(ok=True, message="Logged", external_id="log")


def connector_for(channel: str) -> Connector:
    """
    Returns the connector implementation for a channel; falls back to StubConnector.
    """
    from . import dev, email, feeds, messaging, search, social

    mapping = {
        "twitter": social.TwitterConnector(),
        "linkedin": social.LinkedInConnector(),
        "facebook": social.FacebookConnector(),
        "instagram": social.InstagramConnector(),
        "pinterest": social.PinterestConnector(),
        "reddit": social.RedditConnector(),
        "tiktok": social.TikTokConnector(),
        "telegram": messaging.TelegramConnector(),
        "discord": messaging.DiscordConnector(),
        "slack": messaging.SlackConnector(),
        "whatsapp": messaging.WhatsAppConnector(),
        "mailchimp": email.MailchimpConnector(),
        "sendgrid": email.SendGridConnector(),
        "substack": email.SubstackConnector(),
        "devto": dev.DevtoConnector(),
        "hashnode": dev.HashnodeConnector(),
        "medium": dev.MediumConnector(),
        "gist": dev.GistConnector(),
        "google_indexing": search.GoogleIndexingConnector(),
        "bing_indexing": search.BingConnector(),
        "rss": feeds.RssConnector(),
        "atom": feeds.AtomConnector(),
        "json": feeds.JsonFeedConnector(),
        "websub": feeds.WebSubConnector(),
    }
    return mapping.get(channel) or StubConnector()


def dispatch(job: ShareJob) -> ConnectorResult:
    cfg = get_settings()
    # Honor indexing toggle
    if job.channel in {"google_indexing", "bing_indexing"} and not cfg.get(
        "allow_indexing_jobs", False
    ):
        return ConnectorResult(
            ok=True,
            status_override="skipped",
            message="Indexing jobs disabled in settings",
        )

    # Require an active SocialAccount for channels that need credentials
    account_required = {
        "twitter",
        "linkedin",
        "facebook",
        "instagram",
        "pinterest",
        "reddit",
        "tiktok",
        "telegram",
        "discord",
        "slack",
        "whatsapp",
        "mailchimp",
        "sendgrid",
        "substack",
        "devto",
        "hashnode",
        "medium",
        "gist",
    }
    account = job.account
    if job.channel in account_required:
        if not account or not getattr(account, "is_active", False):
            has_account = SocialAccount.objects.filter(
                channel=job.channel, is_active=True
            ).exists()
            if not has_account:
                return ConnectorResult(
                    ok=True,
                    status_override="skipped",
                    message="No active provider configured for this channel",
                )
            return ConnectorResult(
                ok=True,
                status_override="skipped",
                message="Job has no account assigned; active provider exists but was not linked",
            )
        if not account.access_token:
            return ConnectorResult(
                ok=True,
                status_override="skipped",
                message="Provider configured but missing access_token",
            )

    connector = connector_for(job.channel)
    try:
        result = connector.send(job)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Connector failed for %s", job.channel)
        result = ConnectorResult(ok=False, message=str(exc))
    # If the connector is a stub, treat as a graceful skip to avoid retry storms.
    if isinstance(connector, StubConnector):
        result.ok = True
        result.status_override = "skipped"
        result.message = (
            result.message or f"Connector not implemented for {job.channel}"
        )
    _log(job, result)
    return result
