from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from apps.ai.models import ModelEndpoint, PipelineRun, Workflow


@staff_member_required(login_url="admin_suite:admin_suite_login")
def ops_dashboard(request):
    workflows = Workflow.objects.filter(is_active=True)[:50]
    runs = PipelineRun.objects.order_by("-started_at")[:50]
    endpoints = ModelEndpoint.objects.filter(is_active=True)[:50]
    return render(
        request,
        "ai/ops_dashboard.html",
        {"workflows": workflows, "runs": runs, "endpoints": endpoints},
    )
