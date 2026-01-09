from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.distribution.api import get_settings
from apps.distribution.models import (
    ShareJob,
    ShareLog,
    SharePlan,
    ShareTemplate,
    SocialAccount,
    SyndicationPartner,
)
from apps.distribution.services import _enabled_channels


@staff_member_required(login_url="admin_suite:admin_suite_login")
def dashboard(request):
    accounts = SocialAccount.objects.all()[:50]
    templates = ShareTemplate.objects.all()[:50]
    plans = SharePlan.objects.all()[:50]
    jobs = ShareJob.objects.order_by("-created_at")[:20]
    logs = ShareLog.objects.order_by("-created_at")[:20]
    partners = SyndicationPartner.objects.all()[:20]
    settings_obj = get_settings()
    enabled_channels = set(_enabled_channels())
    active_accounts = SocialAccount.objects.filter(is_active=True)
    active_channels = set(active_accounts.values_list("channel", flat=True))
    missing_channels = sorted(enabled_channels - active_channels)
    missing_credentials = sorted(
        active_accounts.filter(access_token="").values_list("channel", flat=True)
    )
    readiness = {
        "enabled_channels": sorted(enabled_channels),
        "active_channels": sorted(active_channels),
        "missing_channels": missing_channels,
        "missing_credentials": missing_credentials,
        "has_gaps": bool(missing_channels),
    }
    return render(
        request,
        "distribution/dashboard.html",
        {
            "accounts": accounts,
            "templates": templates,
            "plans": plans,
            "jobs": jobs,
            "logs": logs,
            "partners": partners,
            "dist_settings": settings_obj,
            "readiness": readiness,
        },
    )
