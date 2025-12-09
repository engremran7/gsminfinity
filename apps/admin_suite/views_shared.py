"""
Admin Suite shared imports and helpers.

All admin views are staff-gated via STAFF_ONLY unless explicitly public (e.g., login/recovery).
"""

from __future__ import annotations

import csv
import io
import logging
import secrets
from typing import Any, Dict, List

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required as django_staff_member_required
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.utils import timezone

from allauth.account.forms import ResetPasswordForm

from apps.ai.clients import AIProviderError
from apps.ai.models import AISettings
from apps.ai.services import test_completion
from apps.core.cache import DistributedCacheManager
from apps.pages.models import Page
from apps.users.models import SecurityQuestion

logger = logging.getLogger(__name__)

_ADMIN_DISABLED = Http404("Admin suite is disabled.")
_ADMIN_LOGIN_URL = reverse_lazy("admin_suite:admin_suite_login")

# Provide a consistent staff-only decorator that points to the Admin Suite login,
# not the Django admin login (admin:login), to avoid incorrect redirects.
def staff_member_required(view_func=None, redirect_field_name="", login_url=_ADMIN_LOGIN_URL):
    return django_staff_member_required(
        view_func=view_func,
        redirect_field_name=redirect_field_name,
        login_url=login_url,
    )

STAFF_ONLY = staff_member_required


def _make_breadcrumb(*items: tuple[str, str | None]) -> List[Dict[str, str | None]]:
    """
    Build a breadcrumb list from (label, url_name) pairs.
    url_name may be None to render as plain text.
    """
    breadcrumb: List[Dict[str, str | None]] = []
    for label, url_name in items:
        url = None
        if url_name:
            try:
                url = reverse(url_name)
            except Exception:
                url = None
        breadcrumb.append({"label": label, "url": url})
    return breadcrumb


def _render_admin(
    request: HttpRequest,
    template: str,
    context: Dict[str, Any],
    nav_active: str,
    breadcrumb: List[Dict[str, str | None]],
    subtitle: str | None = None,
) -> HttpResponse:
    payload = {
        "nav_active": nav_active,
        "breadcrumb": breadcrumb,
        "subtitle": subtitle,
    }
    payload.update(context or {})
    return render(request, template, payload)
