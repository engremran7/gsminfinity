from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required

from apps.core.models import AppRegistry
from apps.admin_suite.views_shared import (
    _ADMIN_DISABLED,
    _make_breadcrumb,
    _render_admin,
    logger,
)
from apps.distribution.api import get_settings as dist_get_settings
from apps.distribution.forms import SocialAccountForm
from apps.distribution.models import SocialAccount, SharePlan, ShareJob, ShareLog
from apps.distribution.tasks import enqueue_pending_for_account


__all__ = ["admin_suite_distribution"]


@csrf_protect
@staff_member_required
def admin_suite_distribution(request: HttpRequest) -> HttpResponse:
    """Distribution overview with SocialAccount editor and job controls."""
    if not getattr(AppRegistry.get_solo(), "distribution_enabled", True):
        raise _ADMIN_DISABLED

    stats = {
        "accounts": 0,
        "plans": 0,
        "jobs_pending": 0,
        "jobs_failed": 0,
        "logs_24h": 0,
    }
    message = ""
    query = (request.GET.get("q") or "").strip()
    account_form = SocialAccountForm()

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "disable_account":
                aid = request.POST.get("account_id")
                SocialAccount.objects.filter(pk=aid).update(is_active=False)
                message = "Account disabled."
            elif action == "enable_account":
                aid = request.POST.get("account_id")
                SocialAccount.objects.filter(pk=aid).update(is_active=True)
                message = "Account enabled."
            elif action == "save_account":
                aid = request.POST.get("account_id")
                instance = SocialAccount.objects.filter(pk=aid).first() if aid else None
                form = SocialAccountForm(request.POST, instance=instance)
                if form.is_valid():
                    acc = form.save()
                    try:
                        enqueue_pending_for_account(acc)
                    except Exception:
                        logger.debug("enqueue_pending_for_account failed", exc_info=True)
                    message = "Account saved."
                else:
                    message = "Invalid account form."
            elif action == "retry_job":
                jid = request.POST.get("job_id")
                ShareJob.objects.filter(pk=jid).update(status="pending", last_error="")
                message = "Job retried."
            elif action == "cancel_job":
                jid = request.POST.get("job_id")
                ShareJob.objects.filter(pk=jid).update(status="cancelled")
                message = "Job cancelled."
        except Exception as exc:
            logger.warning("Admin suite distribution action failed: %s", exc)
            message = "Action failed."

    try:
        dist_settings = dist_get_settings()
        stats["accounts"] = SocialAccount.objects.count()
        stats["plans"] = SharePlan.objects.count()
        stats["jobs_pending"] = ShareJob.objects.filter(status="pending").count()
        stats["jobs_failed"] = ShareJob.objects.filter(status="failed").count()

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["logs_24h"] = ShareLog.objects.filter(created_at__gte=since).count()

        account_qs = SocialAccount.objects.order_by("channel", "account_name")
        plan_qs = SharePlan.objects.order_by("-created_at")
        jobs_qs = ShareJob.objects.order_by("-created_at")
        logs_qs = ShareLog.objects.order_by("-created_at")
        if query:
            account_qs = account_qs.filter(Q(channel__icontains=query) | Q(account_name__icontains=query))
            plan_qs = plan_qs.filter(Q(post__title__icontains=query))
            jobs_qs = jobs_qs.filter(Q(channel__icontains=query) | Q(status__icontains=query))
            logs_qs = logs_qs.filter(Q(level__icontains=query) | Q(message__icontains=query))

        accounts = account_qs[:50]
        plans = plan_qs[:50]
        jobs = jobs_qs[:50]
        logs = logs_qs[:50]
    except Exception as exc:
        logger.debug("Admin suite distribution snapshot failed: %s", exc)
        dist_settings = {}
        accounts = plans = jobs = logs = []
        message = "Unable to load distribution data."

    return _render_admin(
        request,
        "admin_suite/distribution.html",
        {
            "stats": stats,
            "accounts": accounts,
            "plans": plans,
            "jobs": jobs,
            "logs": logs,
            "query": query,
            "message": message,
            "dist_settings": dist_settings,
            "account_form": account_form,
        },
        nav_active="distribution",
        breadcrumb=_make_breadcrumb(("Distribution", None)),
    )
