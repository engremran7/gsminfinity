from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.distribution.models import SocialAccount, ShareTemplate, SharePlan, ShareJob, ShareLog, SyndicationPartner


@staff_member_required
def dashboard(request):
    accounts = SocialAccount.objects.all()[:50]
    templates = ShareTemplate.objects.all()[:50]
    plans = SharePlan.objects.all()[:50]
    jobs = ShareJob.objects.order_by("-created_at")[:20]
    logs = ShareLog.objects.order_by("-created_at")[:20]
    partners = SyndicationPartner.objects.all()[:20]
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
        },
    )
