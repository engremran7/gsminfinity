# Distribution App

Syndication connectors scaffold for email/newsletter/feeds/social with admin-suite controls.

## Capabilities
- Models: SocialAccount, SharePlan, ShareJob, ShareLog, DistributionSettings (require_admin_approval, retries, default channels).
- Signals/tasks: enqueue pending jobs when accounts become active; log-only connectors by default.
- Admin suite distribution page: manage SocialAccounts (tokens/config), enable/disable, retry/cancel jobs, view settings/stats.

## Key Files
- `models.py` — Accounts/plans/jobs/logs/settings.
- `forms.py` — SocialAccountForm (DB-stored tokens/config).
- `tasks.py` — enqueue helpers (Celery-friendly, fallback).
- `connectors/*` — Logging connectors; placeholders for real APIs.
- `signals.py` — Hooks on SocialAccount activation.
- `management/commands/distribution_jobs.py` — Retry/cancel/stats CLI.

## Notes
- Connectors are log-only until real API code/credentials are added.
- Per-account posting intervals and retries configurable via settings.
