from __future__ import annotations


from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_protect

from .views_shared import STAFF_ONLY, _ADMIN_DISABLED, _make_breadcrumb, _render_admin
# Extracted views_settings views from legacy views.py
@staff_member_required
def admin_suite_settings(request: HttpRequest) -> HttpResponse:
    """Settings and security flags overview."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    site_snapshot: Dict[str, Any] = {}
    message = ""
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.core.models import AppRegistry

            reg = AppRegistry.get_solo()
            if action and hasattr(reg, action):
                current = bool(getattr(reg, action))
                setattr(reg, action, not current)
                reg.save(update_fields=[action])
                message = f"{action} set to {not current}"
        except Exception as exc:
            logger.warning("Admin suite registry toggle failed: %s", exc)
            message = "Toggle failed."
    try:
        from apps.site_settings.models import SiteSettings

        ss = SiteSettings.get_solo()
        site_snapshot = {
            "site_name": getattr(ss, "site_name", "Site"),
            "site_header": getattr(ss, "site_header", ""),
            "site_description": getattr(ss, "site_description", ""),
            "primary_color": getattr(ss, "primary_color", "#0d6efd") or "#0d6efd",
            "secondary_color": getattr(ss, "secondary_color", "#6c757d") or "#6c757d",
            "enable_signup": bool(getattr(ss, "enable_signup", True)),
            "maintenance_mode": bool(getattr(ss, "maintenance_mode", False)),
            "force_https": bool(getattr(ss, "force_https", False)),
            "cache_ttl_seconds": getattr(ss, "cache_ttl_seconds", 600),
        }
    except Exception as exc:
        logger.warning("Admin suite site settings snapshot failed: %s", exc)

    security_status = {
        "devices_enabled": False,
        "bots_enabled": False,
        "risk_enabled": False,
        "login_policy": "mfa_if_high",
        "ads_enabled": True,
        "seo_enabled": True,
        "comments_enabled": True,
        "distribution_enabled": True,
        "device_identity_enabled": True,
        "crawler_guard_enabled": True,
        "ai_behavior_enabled": True,
    }
    try:
        from security_suite.security import conf as sec_conf
        from security_suite.security_bots import conf as bot_conf
        from security_suite.security_devices import conf as dev_conf
        from security_suite.security_risk import conf as risk_conf

        from apps.core.models import AppRegistry

        reg = AppRegistry.get_solo()
        security_status.update(
            {
                "devices_enabled": dev_conf.get("PERSISTENCE_ENABLED", True),
                "bots_enabled": bot_conf.get("ENABLED", True),
                "risk_enabled": risk_conf.get("ENABLED", True),
                "login_policy": sec_conf.get(
                    "DEFAULT_LOGIN_RISK_POLICY", "mfa_if_high"
                ),
                "ads_enabled": bool(getattr(reg, "ads_enabled", True)),
                "seo_enabled": bool(getattr(reg, "seo_enabled", True)),
                "comments_enabled": bool(getattr(reg, "comments_enabled", True)),
                "distribution_enabled": bool(
                    getattr(reg, "distribution_enabled", True)
                ),
                "device_identity_enabled": bool(
                    getattr(reg, "device_identity_enabled", True)
                ),
                "crawler_guard_enabled": bool(
                    getattr(reg, "crawler_guard_enabled", True)
                ),
                "ai_behavior_enabled": bool(getattr(reg, "ai_behavior_enabled", True)),
            }
        )
    except Exception as exc:
        logger.debug("Admin suite security snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/settings.html",
        {
            "site_snapshot": site_snapshot,
            "security_status": security_status,
            "message": message,
        },
        nav_active="settings",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Settings", None)
        ),
    )


@staff_member_required
def admin_suite_settings_edit(request: HttpRequest) -> HttpResponse:
    """Edit SiteSettings with a constrained form and cache invalidation."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    class SettingsForm(forms.Form):
        site_name = forms.CharField(max_length=100, required=True)
        site_header = forms.CharField(max_length=100, required=False)
        site_description = forms.CharField(max_length=500, required=False)
        primary_color = forms.CharField(max_length=7, required=False)
        secondary_color = forms.CharField(max_length=7, required=False)
        enable_signup = forms.BooleanField(required=False)
        maintenance_mode = forms.BooleanField(required=False)
        force_https = forms.BooleanField(required=False)
        cache_ttl_seconds = forms.IntegerField(
            required=False, min_value=60, max_value=86400
        )

    instance = None
    initial = {}
    try:
        from apps.site_settings.models import SiteSettings

        instance = SiteSettings.get_solo()
        initial = {
            "site_name": getattr(instance, "site_name", ""),
            "site_header": getattr(instance, "site_header", ""),
            "site_description": getattr(instance, "site_description", ""),
            "primary_color": getattr(instance, "primary_color", ""),
            "secondary_color": getattr(instance, "secondary_color", ""),
            "enable_signup": bool(getattr(instance, "enable_signup", True)),
            "maintenance_mode": bool(getattr(instance, "maintenance_mode", False)),
            "force_https": bool(getattr(instance, "force_https", False)),
            "cache_ttl_seconds": getattr(instance, "cache_ttl_seconds", 600),
        }
    except Exception as exc:
        logger.warning("Admin suite settings load failed: %s", exc)

    if request.method == "POST":
        form = SettingsForm(request.POST)
        if form.is_valid() and instance:
            cleaned = form.cleaned_data
            for field, value in cleaned.items():
                setattr(instance, field, value)
            try:
                instance.save()
                try:
                    DistributedCacheManager.invalidate_site_settings()
                except Exception:
                    pass
                return redirect("admin_suite:admin_suite_settings")
            except Exception as exc:
                form.add_error(None, f"Save failed: {exc}")
    else:
        form = SettingsForm(initial=initial)

    return _render_admin(
        request,
        "admin_suite/settings_edit.html",
        {
            "form": form,
        },
        nav_active="settings",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Settings", "admin_suite:admin_suite_settings"),
            ("Edit", None),
        ),
    )


@staff_member_required
def admin_suite_consent(request: HttpRequest) -> HttpResponse:
    """Consent overview: policies and recent decisions/events (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "policies_total": 0,
        "policies_active": 0,
        "decisions_24h": 0,
    }
    policies: list[Dict[str, Any]] = []
    decisions: list[Dict[str, Any]] = []
    events: list[Dict[str, Any]] = []

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from django.utils import timezone

            from apps.consent.models import ConsentPolicy

            if action == "create_policy":
                ConsentPolicy.objects.create(
                    version=(request.POST.get("version") or "")[:50],
                    site_domain=(request.POST.get("site_domain") or "")[:255],
                    is_active=bool(request.POST.get("is_active")),
                    banner_text=(request.POST.get("banner_text") or "")[:255],
                    manage_text=(request.POST.get("manage_text") or "")[:255],
                    cache_ttl_seconds=int(request.POST.get("cache_ttl_seconds") or 600),
                    text=request.POST.get("text") or "",
                    effective_from=request.POST.get("effective_from") or timezone.now(),
                )
            elif action == "update_policy":
                pid = request.POST.get("policy_id")
                ConsentPolicy.objects.filter(pk=pid).update(
                    site_domain=(request.POST.get("site_domain") or "")[:255],
                    is_active=bool(request.POST.get("is_active")),
                    banner_text=(request.POST.get("banner_text") or "")[:255],
                    manage_text=(request.POST.get("manage_text") or "")[:255],
                    cache_ttl_seconds=int(request.POST.get("cache_ttl_seconds") or 600),
                    text=request.POST.get("text") or "",
                )
        except Exception as exc:
            logger.warning("Admin suite consent action failed: %s", exc)

    try:
        from django.utils import timezone

        from apps.consent.models import ConsentDecision, ConsentEvent, ConsentPolicy

        stats["policies_total"] = ConsentPolicy.objects.count()
        stats["policies_active"] = ConsentPolicy.objects.filter(is_active=True).count()

        policies = list(
            ConsentPolicy.objects.order_by("-effective_from")[:10].values(
                "id", "version", "site_domain", "is_active", "effective_from"
            )
        )

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["decisions_24h"] = ConsentDecision.objects.filter(
            created_at__gte=since
        ).count()
        decisions = list(
            ConsentDecision.objects.select_related("user", "policy")
            .order_by("-created_at")[:10]
            .values(
                "created_at",
                "user__email",
                "session_id",
                "policy__version",
            )
        )

        events = list(
            ConsentEvent.objects.select_related("policy")
            .order_by("-created_at")[:10]
            .values("event_type", "created_at", "policy__version")
        )
    except Exception as exc:
        logger.debug("Admin suite consent snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/consent.html",
        {
            "stats": stats,
            "policies": policies,
            "decisions": decisions,
            "events": events,
        },
        nav_active="consent",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Consent", None)
        ),
        subtitle="Policies, decisions, and banner health",
    )


@staff_member_required
def admin_suite_email_settings(request: HttpRequest) -> HttpResponse:
    """Manage Gmail SMTP settings from SiteSettings."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    class EmailForm(forms.Form):
        gmail_enabled = forms.BooleanField(required=False)
        gmail_username = forms.EmailField(required=False)
        gmail_app_password = forms.CharField(
            widget=forms.PasswordInput(render_value=False), required=False
        )
        gmail_from_email = forms.EmailField(required=False)

    instance = None
    initial: Dict[str, Any] = {}
    try:
        from apps.site_settings.models import SiteSettings

        instance = SiteSettings.get_solo()
        initial = {
            "gmail_enabled": bool(getattr(instance, "gmail_enabled", False)),
            "gmail_username": getattr(instance, "gmail_username", "") or "",
            "gmail_app_password": getattr(instance, "gmail_app_password", "") or "",
            "gmail_from_email": getattr(instance, "gmail_from_email", "") or "",
        }
    except Exception as exc:
        logger.warning("Admin suite email settings load failed: %s", exc)

    if request.method == "POST":
        form = EmailForm(request.POST)
        if form.is_valid() and instance:
            data = form.cleaned_data
            try:
                instance.gmail_enabled = bool(data.get("gmail_enabled"))
                instance.gmail_username = data.get("gmail_username", "") or ""
                instance.gmail_app_password = data.get("gmail_app_password", "") or ""
                instance.gmail_from_email = data.get("gmail_from_email", "") or ""
                instance.save(
                    update_fields=[
                        "gmail_enabled",
                        "gmail_username",
                        "gmail_app_password",
                        "gmail_from_email",
                        "updated_at",
                    ]
                )
                try:
                    DistributedCacheManager.invalidate_site_settings()
                except Exception:
                    pass
                messages.success(request, "Email settings updated.")
                return redirect("admin_suite:admin_suite_email_settings")
            except Exception as exc:
                form.add_error(None, f"Save failed: {exc}")
    else:
        form = EmailForm(initial=initial)

    return _render_admin(
        request,
        "admin_suite/email_settings.html",
        {"form": form},
        nav_active="settings_email",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Settings", "admin_suite:admin_suite_settings"),
            ("Email & Delivery", None),
        ),
        subtitle="Configure Gmail SMTP (app password)",
    )


__all__ = [
    "admin_suite_settings",
    "admin_suite_settings_edit",
    "admin_suite_consent",
    "admin_suite_email_settings",
]
