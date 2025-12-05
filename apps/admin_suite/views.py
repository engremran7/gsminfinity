"""
Admin Suite views.

All views are staff-gated and controlled by the ADMIN_SUITE_ENABLED feature flag.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List

from django import forms
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.core.cache import DistributedCacheManager
from apps.pages.models import Page

logger = logging.getLogger(__name__)

_ADMIN_DISABLED = Http404("Admin suite is disabled.")


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


@staff_member_required
def admin_suite_command_search(request: HttpRequest) -> JsonResponse:
    """
    Lightweight command palette endpoint returning admin shortcuts.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    try:
        cache_key = f"admin_cmd_throttle_{getattr(request.user, 'id', 'anon')}_{request.META.get('REMOTE_ADDR', '')}"
        if cache.get(cache_key):
            return JsonResponse({"error": "rate_limited"}, status=429)
        cache.set(cache_key, True, timeout=2)
    except Exception:
        pass

    shortcuts = [
        ("Admin Home", "admin_suite:admin_suite", "overview home"),
        ("Security Overview", "admin_suite:admin_suite_security", "security"),
        ("Devices", "admin_suite:admin_suite_security_devices", "security devices"),
        ("Crawler Guard", "admin_suite:admin_suite_security_crawlers", "security bots"),
        ("Risk Insights", "admin_suite:admin_suite_security_risk", "security risk"),
        ("Users", "admin_suite:admin_suite_users", "users accounts"),
        ("Consent", "admin_suite:admin_suite_consent", "privacy consent"),
        ("Pages", "admin_suite:admin_suite_pages", "pages cms"),
        ("Blog", "admin_suite:admin_suite_blog", "blog posts"),
        ("Content", "admin_suite:admin_suite_content", "content posts comments"),
        ("Comments", "admin_suite:admin_suite_comments", "content comments moderation"),
        ("Marketing", "admin_suite:admin_suite_marketing", "marketing"),
        ("Ads", "admin_suite:admin_suite_ads", "ads placements creatives"),
        ("SEO", "admin_suite:admin_suite_seo", "seo redirects sitemap"),
        ("Tags", "admin_suite:admin_suite_tags", "tags taxonomy"),
        ("Distribution", "admin_suite:admin_suite_distribution", "distribution syndication"),
        ("App Registry", "admin_suite:admin_suite_registry", "registry flags"),
        ("Settings", "admin_suite:admin_suite_settings", "settings site brand"),
    ]

    q = (request.GET.get("q") or "").lower().strip()
    results = []
    for label, url_name, tags in shortcuts:
        try:
            url = reverse(url_name)
        except Exception:
            continue
        haystack = f"{label.lower()} {tags}"
        if q and q not in haystack:
            continue
        results.append({"label": label, "url": url, "tags": tags})

    return JsonResponse({"results": results[:25]})

# =====================================================================
# Admin Suite Shell
# =====================================================================
@staff_member_required
def admin_suite(request: HttpRequest) -> HttpResponse:
    """
    Minimal shell for the custom admin suite.
    Gated to staff and controlled by ADMIN_SUITE_ENABLED.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    security_status = {
        "devices_enabled": False,
        "bots_enabled": False,
        "risk_enabled": False,
        "login_policy": "mfa_if_high",
    }
    try:
        from security_suite.security import conf as sec_conf

        security_status.update(
            {
                "devices_enabled": sec_conf.get("DEVICES_ENABLED", True),
                "bots_enabled": sec_conf.get("BOTS_ENABLED", True),
                "risk_enabled": sec_conf.get("RISK_ENABLED", True),
                "login_policy": sec_conf.get("DEFAULT_LOGIN_RISK_POLICY", "mfa_if_high"),
            }
        )
    except Exception:
        pass

    return _render_admin(
        request,
        "admin_suite/index.html",
        {
            "security_status": security_status,
        },
        nav_active="overview",
        breadcrumb=_make_breadcrumb(("Admin Home", None)),
        subtitle="Overview of security, content, and operations",
    )


@csrf_protect
@staff_member_required
def admin_suite_security(request: HttpRequest) -> HttpResponse:
    """
    Security suite overview and management for Devices, Crawler Guard, and Risk.
    Consolidates actions and tables into a single tab with anchor sections.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    class DeviceActionForm(forms.Form):
        action = forms.ChoiceField(
            choices=[
                ("block", "block"),
                ("unblock", "unblock"),
                ("trust", "trust"),
                ("untrust", "untrust"),
                ("reset_quota", "reset_quota"),
            ]
        )
        device_id = forms.CharField(required=False)
        user_id = forms.IntegerField(required=False)

    class CrawlerRuleForm(forms.Form):
        action = forms.ChoiceField(choices=[("enable", "enable"), ("disable", "disable"), ("create", "create")])
        rule_id = forms.CharField(required=False)
        name = forms.CharField(required=False, max_length=100)
        path_pattern = forms.RegexField(required=False, regex=r"^[\\w./*-]+$", max_length=255)
        requests_per_minute = forms.IntegerField(required=False, min_value=1, max_value=6000)

    message = ""
    registry_flags = {
        "device_identity_enabled": None,
        "crawler_guard_enabled": None,
        "ai_behavior_enabled": None,
    }
    device_config: Dict[str, Any] = {}
    security_config: Dict[str, Any] = {}

    # Handle POST actions across devices, crawler rules, and risk insights
    if request.method == "POST":
        action = request.POST.get("action") or ""
        if request.POST.get("insight_id"):
            insight_id = request.POST.get("insight_id")
            new_status = request.POST.get("status")
            if insight_id and new_status in {"open", "approved", "rejected", "resolved"}:
                try:
                    from apps.ai_behavior.models import BehaviorInsight

                    insight = BehaviorInsight.objects.filter(pk=insight_id).first()
                    if insight:
                        insight.status = new_status
                        insight.save(update_fields=["status"])
                        message = f"Insight {insight_id} set to {new_status}."
                        logger.info(
                            "admin_suite_risk_insight",
                            extra={"insight_id": insight_id, "status": new_status, "staff_user": getattr(request.user, "email", None)},
                        )
                except Exception as exc:
                    logger.warning("Admin suite risk action failed: %s", exc)
                    message = "Action failed."
        elif action in {"block", "unblock", "trust", "untrust", "reset_quota"}:
            try:
                form = DeviceActionForm(request.POST)
                if form.is_valid():
                    cleaned = form.cleaned_data
                    device_id = cleaned.get("device_id")
                    user_id = cleaned.get("user_id")
                    from apps.devices.models import Device
                    from apps.devices.models_quota import UserDeviceQuota

                    if action == "reset_quota" and user_id:
                        quota, _ = UserDeviceQuota.objects.get_or_create(user_id=user_id)
                        quota.last_reset_at = timezone.now()
                        quota.save(update_fields=["last_reset_at"])
                        message = f"Quota reset for user {user_id}."
                        logger.info(
                            "admin_suite_device_quota_reset",
                            extra={
                                "user_id": str(user_id),
                                "action": action,
                                "staff_user": getattr(request.user, "email", None),
                            },
                        )
                    elif device_id:
                        device = Device.objects.filter(pk=device_id).first()
                        if device:
                            if action == "block":
                                device.is_blocked = True
                            elif action == "unblock":
                                device.is_blocked = False
                            elif action == "trust":
                                device.is_trusted = True
                            elif action == "untrust":
                                device.is_trusted = False
                            device.save(update_fields=["is_blocked", "is_trusted"])
                            message = f"Device {device_id} updated ({action})."
                            logger.info(
                                "admin_suite_device_action",
                                extra={
                                    "device_id": str(device_id),
                                    "action": action,
                                    "staff_user": getattr(request.user, "email", None),
                                },
                            )
            except Exception as exc:
                logger.warning("Admin suite device action failed: %s", exc)
                message = "Action failed."
        elif action in {"enable", "disable", "create"}:
            form = CrawlerRuleForm(request.POST)
            if form.is_valid():
                cleaned = form.cleaned_data
                rule_id = cleaned.get("rule_id")
                try:
                    from apps.crawler_guard.models import CrawlerRule

                    if action in {"enable", "disable"} and rule_id:
                        rule = CrawlerRule.objects.filter(pk=rule_id).first()
                        if rule:
                            rule.is_enabled = action == "enable"
                            rule.save(update_fields=["is_enabled"])
                            message = f"Rule {rule_id} {action}d."
                            logger.info(
                                "admin_suite_crawler_rule",
                                extra={
                                    "rule_id": rule_id,
                                    "action": action,
                                    "staff_user": getattr(request.user, "email", None),
                                },
                            )
                    elif action == "create":
                        rpm = cleaned.get("requests_per_minute") or 60
                        CrawlerRule.objects.create(
                            name=(cleaned.get("name") or "")[:100],
                            path_pattern=(cleaned.get("path_pattern") or "")[:255],
                            requests_per_minute=rpm,
                        )
                        message = "Rule created."
                except Exception as exc:
                    logger.warning("Admin suite crawler action failed: %s", exc)
                    message = "Action failed."
        elif action == "toggle_flag":
            flag = request.POST.get("flag")
            try:
                from apps.core.models import AppRegistry

                if flag in {"device_identity_enabled", "crawler_guard_enabled", "ai_behavior_enabled"}:
                    reg = AppRegistry.get_solo()
                    current = bool(getattr(reg, flag))
                    setattr(reg, flag, not current)
                    reg.save(update_fields=[flag])
                    registry_flags[flag] = not current
                    message = f"{flag} set to {not current}"
                    logger.info(
                        "admin_suite_security_toggle_flag",
                        extra={"flag": flag, "value": not current, "staff_user": getattr(request.user, "email", None)},
                    )
            except Exception as exc:
                logger.warning("Admin suite security toggle failed: %s", exc)
                message = "Toggle failed."
        elif action == "update_security_config":
            try:
                from apps.security_suite.models import SecurityConfig

                cfg = SecurityConfig.get_solo()
                cfg.devices_enabled = bool(request.POST.get("devices_enabled"))
                cfg.crawler_guard_enabled = bool(request.POST.get("crawler_guard_enabled"))
                cfg.mfa_enabled = bool(request.POST.get("mfa_enabled"))
                cfg.login_risk_enabled = bool(request.POST.get("login_risk_enabled"))
                cfg.device_quota_enforcement_enabled = bool(request.POST.get("device_quota_enforcement_enabled"))
                try:
                    cfg.default_device_limit = max(1, int(request.POST.get("default_device_limit") or cfg.default_device_limit))
                except Exception:
                    pass
                window = request.POST.get("default_device_window") or cfg.default_device_window
                if window in {"3m", "6m", "12m"}:
                    cfg.default_device_window = window
                c_action = request.POST.get("crawler_default_action") or cfg.crawler_default_action
                if c_action in {"allow", "throttle", "block", "challenge"}:
                    cfg.crawler_default_action = c_action
                tier = request.POST.get("security_tier") or cfg.security_tier
                if tier in {"basic", "standard", "strict"}:
                    cfg.security_tier = tier
                mfa_policy = request.POST.get("mfa_policy") or cfg.mfa_policy
                if mfa_policy in {"optional", "mfa_if_high", "required"}:
                    cfg.mfa_policy = mfa_policy
                risk_policy = request.POST.get("login_risk_policy") or cfg.login_risk_policy
                if risk_policy in {"none", "info", "mfa_if_high", "block_if_high"}:
                    cfg.login_risk_policy = risk_policy
                cfg.save()
                message = "Security config updated."
                logger.info(
                    "admin_suite_security_config_updated",
                    extra={"staff_user": getattr(request.user, "email", None)},
                )
            except Exception as exc:
                logger.warning("Admin suite security config update failed: %s", exc)
                message = "Security config update failed."
        elif action == "update_device_config":
            try:
                from apps.devices.models import DeviceConfig

                cfg = DeviceConfig.get_solo()
                cfg.basic_fingerprinting_enabled = bool(request.POST.get("basic_fingerprinting_enabled"))
                cfg.enhanced_fingerprinting_enabled = bool(request.POST.get("enhanced_fingerprinting_enabled"))
                cfg.enterprise_device_management_enabled = bool(request.POST.get("enterprise_device_management_enabled"))
                try:
                    cfg.max_devices_default = max(1, int(request.POST.get("max_devices_default") or cfg.max_devices_default))
                except Exception:
                    pass
                for field in ["monthly_device_quota", "yearly_device_quota"]:
                    raw = request.POST.get(field)
                    if raw in {"", None}:
                        setattr(cfg, field, None)
                    else:
                        try:
                            setattr(cfg, field, max(1, int(raw)))
                        except Exception:
                            pass
                cfg.save()
                message = "Device settings updated."
            except Exception as exc:
                logger.warning("Admin suite device config update failed: %s", exc)
                message = "Device settings update failed."

    # Defaults
    stats = {
        "devices_total": 0,
        "devices_blocked": 0,
        "crawler_events_24h": 0,
        "risk_insights_open": 0,
    }
    device_events: list[Dict[str, Any]] = []
    crawler_events: list[Dict[str, Any]] = []
    risk_insights: list[Dict[str, Any]] = []
    devices: list[Dict[str, Any]] = []
    rules: list[Dict[str, Any]] = []
    security_events: list[Dict[str, Any]] = []
    device_window_choices = [("3m", "3 Months"), ("6m", "6 Months"), ("12m", "12 Months")]
    security_tier_choices = [("basic", "Basic"), ("standard", "Standard"), ("strict", "Strict")]
    mfa_policy_choices = [("optional", "Optional"), ("mfa_if_high", "MFA if High"), ("required", "Required")]
    login_risk_policy_choices = [("none", "None"), ("info", "Info Only"), ("mfa_if_high", "MFA if High"), ("block_if_high", "Block if High")]
    crawler_action_choices = [("allow", "Allow"), ("throttle", "Throttle"), ("block", "Block"), ("challenge", "Challenge")]

    # Pagination (devices)
    page = 1
    page_size = 25
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25

    offset = (page - 1) * page_size

    # Devices snapshot + list
    # Devices snapshot
    try:
        from apps.devices.models import Device, DeviceEvent

        stats["devices_total"] = Device.objects.count()
        stats["devices_blocked"] = Device.objects.filter(is_blocked=True).count()
        device_events = list(
            DeviceEvent.objects.select_related("device")
            .order_by("-created_at")[:10]
            .values("event_type", "success", "reason", "created_at", "device_id")
        )
        devices = list(
            Device.objects.order_by("-last_seen_at")
            .values(
                "id",
                "user_id",
                "machine_uuid",
                "display_name",
                "is_trusted",
                "is_blocked",
                "risk_score",
                "last_seen_at",
            )[offset : offset + page_size]
        )
    except Exception as exc:
        logger.debug("Admin suite devices snapshot failed: %s", exc)

    # Crawler guard snapshot
    try:
        from apps.crawler_guard.models import CrawlerEvent, CrawlerRule
        from django.utils import timezone

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["crawler_events_24h"] = CrawlerEvent.objects.filter(created_at__gte=since).count()
        crawler_events = list(
            CrawlerEvent.objects.order_by("-created_at")[:10].values(
                "ip", "action_taken", "path", "created_at"
            )
        )
        rules = list(
            CrawlerRule.objects.order_by("-priority", "name").values(
                "id", "name", "path_pattern", "requests_per_minute", "action", "is_enabled", "priority"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite crawler snapshot failed: %s", exc)

    # Risk insights snapshot
    try:
        from apps.ai_behavior.models import BehaviorInsight

        stats["risk_insights_open"] = BehaviorInsight.objects.filter(status="open").count()
        risk_insights = list(
            BehaviorInsight.objects.order_by("-created_at")[:10].values(
                "severity", "status", "created_at", "related_user_id", "device_identifier"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite risk snapshot failed: %s", exc)

    # Security events snapshot
    try:
        from apps.security_events.models import SecurityEvent

        security_events = list(
            SecurityEvent.objects.select_related("user", "device")
            .order_by("-created_at")[:20]
            .values("type", "user_id", "device_id", "ip", "created_at")
        )
    except Exception as exc:
        logger.debug("Admin suite security events snapshot failed: %s", exc)

    # Device config snapshot
    try:
        from apps.devices.models import DeviceConfig

        cfg = DeviceConfig.get_solo()
        device_config = {
            "basic_fingerprinting_enabled": bool(getattr(cfg, "basic_fingerprinting_enabled", True)),
            "enhanced_fingerprinting_enabled": bool(getattr(cfg, "enhanced_fingerprinting_enabled", False)),
            "enterprise_device_management_enabled": bool(getattr(cfg, "enterprise_device_management_enabled", False)),
            "max_devices_default": getattr(cfg, "max_devices_default", 5),
            "monthly_device_quota": getattr(cfg, "monthly_device_quota", None),
            "yearly_device_quota": getattr(cfg, "yearly_device_quota", None),
        }
    except Exception:
        device_config = {}

    # Security config snapshot
    try:
        from apps.security_suite.models import SecurityConfig

        cfg = SecurityConfig.get_solo()
        security_config = {
            "devices_enabled": bool(getattr(cfg, "devices_enabled", True)),
            "crawler_guard_enabled": bool(getattr(cfg, "crawler_guard_enabled", False)),
            "mfa_enabled": bool(getattr(cfg, "mfa_enabled", True)),
            "login_risk_enabled": bool(getattr(cfg, "login_risk_enabled", False)),
            "device_quota_enforcement_enabled": bool(getattr(cfg, "device_quota_enforcement_enabled", False)),
            "default_device_limit": getattr(cfg, "default_device_limit", 5),
            "default_device_window": getattr(cfg, "default_device_window", "12m"),
            "security_tier": getattr(cfg, "security_tier", "basic"),
            "crawler_default_action": getattr(cfg, "crawler_default_action", "allow"),
            "mfa_policy": getattr(cfg, "mfa_policy", "optional"),
            "login_risk_policy": getattr(cfg, "login_risk_policy", "mfa_if_high"),
        }
    except Exception:
        security_config = {}
    if not security_config:
        security_config = {
            "devices_enabled": True,
            "crawler_guard_enabled": False,
            "mfa_enabled": True,
            "login_risk_enabled": False,
            "device_quota_enforcement_enabled": False,
            "default_device_limit": 5,
            "default_device_window": "12m",
            "security_tier": "basic",
            "crawler_default_action": "allow",
            "mfa_policy": "optional",
            "login_risk_policy": "mfa_if_high",
        }

    # Registry flags snapshot (unless already set via toggle)
    try:
        from apps.core.models import AppRegistry

        reg = AppRegistry.get_solo()
        for key in registry_flags.keys():
            if registry_flags[key] is None:
                registry_flags[key] = getattr(reg, key, None)
    except Exception:
        pass

    disabled_labels: list[str] = []
    try:
        label_map = {
            "device_identity_enabled": "Device identity",
            "crawler_guard_enabled": "Crawler guard",
            "ai_behavior_enabled": "AI behavior/risk",
        }
        for key, label in label_map.items():
            if registry_flags.get(key) is False:
                disabled_labels.append(label)
    except Exception:
        disabled_labels = []

    return _render_admin(
        request,
        "admin_suite/security.html",
        {
            "stats": stats,
            "device_events": device_events,
            "crawler_events": crawler_events,
            "risk_insights": risk_insights,
            "devices": devices,
            "rules": rules,
            "page": page,
            "page_size": page_size,
            "message": message,
            "risk_statuses": ["open", "approved", "rejected", "resolved"],
            "registry_flags": registry_flags,
            "disabled_labels": disabled_labels,
            "device_config": device_config,
            "security_config": security_config,
            "security_events": security_events,
            "device_window_choices": device_window_choices,
            "security_tier_choices": security_tier_choices,
            "mfa_policy_choices": mfa_policy_choices,
            "login_risk_policy_choices": login_risk_policy_choices,
            "crawler_action_choices": crawler_action_choices,
        },
        nav_active="security",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Security", None)),
        subtitle="Devices, bots, and AI behavior/risk controls",
    )


@csrf_protect
@staff_member_required
def admin_suite_security_devices(request: HttpRequest) -> HttpResponse:
    """Legacy route: redirect to consolidated security tab with anchor."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED
    return redirect(f"{reverse('admin_suite:admin_suite_security')}#devices")


@csrf_protect
@staff_member_required
def admin_suite_security_crawlers(request: HttpRequest) -> HttpResponse:
    """Legacy route: redirect to consolidated security tab with anchor."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED
    return redirect(f"{reverse('admin_suite:admin_suite_security')}#crawlers")


@csrf_protect
@staff_member_required
def admin_suite_security_risk(request: HttpRequest) -> HttpResponse:
    """Legacy route: redirect to consolidated security tab with anchor."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED
    return redirect(f"{reverse('admin_suite:admin_suite_security')}#risk")


@staff_member_required
def admin_suite_users(request: HttpRequest) -> HttpResponse:
    """Users overview for the admin suite (read-only metrics + paginated list)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "total_users": 0,
        "staff_users": 0,
        "active_users": 0,
        "local_users": 0,
        "social_users": 0,
    }
    users_page: list[Dict[str, Any]] = []
    page = 1
    page_size = 25
    query = (request.GET.get("q") or "").strip()
    provider_filter = (request.GET.get("provider") or "all").lower()
    if provider_filter not in {"all", "local", "social"}:
        provider_filter = "all"
    message = ""
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25

    if request.method == "POST" and request.POST.get("action") == "create_user":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        make_staff = bool(request.POST.get("is_staff"))
        if not email or len(password) < 10:
            message = "Email and password (min 10 chars) required."
        else:
            try:
                from apps.users.models import CustomUser

                user = CustomUser.objects.create_user(email=email, password=password)
                if make_staff and getattr(request.user, "is_superuser", False):
                    user.is_staff = True
                    user.save(update_fields=["is_staff"])
                elif make_staff:
                    message = "Staff flag requires superuser."
                message = "User created."
            except Exception as exc:
                message = f"Create failed: {exc}"

    try:
        from django.db.models import BooleanField, Exists, OuterRef, Q, Value
        from apps.users.models import CustomUser

        stats["total_users"] = CustomUser.objects.count()
        stats["staff_users"] = CustomUser.objects.filter(is_staff=True).count()
        stats["active_users"] = CustomUser.objects.filter(is_active=True).count()

        offset = (page - 1) * page_size
        qs = CustomUser.objects.only(
            "id", "email", "last_login", "date_joined", "is_staff", "is_active"
        ).order_by("-date_joined")

        try:
            from allauth.socialaccount.models import SocialAccount

            qs = qs.annotate(has_social=Exists(SocialAccount.objects.filter(user_id=OuterRef("id"))))
        except Exception:
            SocialAccount = None  # type: ignore
            qs = qs.annotate(has_social=Value(False, output_field=BooleanField()))

        if provider_filter == "local":
            qs = qs.filter(has_social=False)
        elif provider_filter == "social":
            qs = qs.filter(has_social=True)

        if query:
            qs = qs.filter(Q(email__icontains=query) | Q(id__icontains=query))

        # CSV export (lightweight, capped to 5000 rows)
        if request.GET.get("export") == "csv":
            try:
                throttle_key = f"admin_users_export_{getattr(request.user, 'id', 'anon')}_{request.META.get('REMOTE_ADDR', '')}"
                if cache.get(throttle_key):
                    return HttpResponse("rate_limited", status=429)
                cache.set(throttle_key, True, timeout=10)
            except Exception:
                pass
            export_qs = qs[:5000]
            rows = list(
                export_qs.values(
                    "id", "email", "last_login", "date_joined", "is_staff", "is_active", "has_social"
                )
            )
            providers_map: Dict[int, list[str]] = {}
            if rows and "SocialAccount" in locals() and SocialAccount:
                user_ids = [u["id"] for u in rows]
                for row in SocialAccount.objects.filter(user_id__in=user_ids).values("user_id", "provider"):
                    providers_map.setdefault(row["user_id"], []).append(row["provider"])

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="users.csv"'
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(
                ["id", "email", "providers", "is_staff", "is_active", "date_joined", "last_login"]
            )
            for u in rows:
                providers = providers_map.get(u["id"], []) if providers_map else []
                writer.writerow(
                    [
                        u["id"],
                        u["email"],
                        ",".join(providers) if providers else ("social" if u["has_social"] else "local"),
                        u["is_staff"],
                        u["is_active"],
                        u["date_joined"],
                        u["last_login"],
                    ]
                )
            response.write(buf.getvalue())
            return response

        raw_users = list(
            qs[offset : offset + page_size].values(
                "id", "email", "last_login", "date_joined", "is_staff", "is_active", "has_social"
            )
        )

        providers_map: Dict[int, list[str]] = {}
        if raw_users and "SocialAccount" in locals() and SocialAccount:
            user_ids = [u["id"] for u in raw_users]
            for row in SocialAccount.objects.filter(user_id__in=user_ids).values("user_id", "provider"):
                providers_map.setdefault(row["user_id"], []).append(row["provider"])

        # high-level counts for current filtered population (approx on page slice)
        stats["local_users"] = len([u for u in raw_users if not u.get("has_social")])
        stats["social_users"] = len([u for u in raw_users if u.get("has_social")])

        for u in raw_users:
            u["providers"] = providers_map.get(u["id"], []) if providers_map else []
            users_page.append(u)
    except Exception as exc:
        logger.warning("Admin suite users snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/users.html",
        {
            "stats": stats,
            "users_page": users_page,
            "page": page,
            "page_size": page_size,
            "q": query,
            "provider_filter": provider_filter,
            "message": message,
        },
        nav_active="users",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Users", None)),
        subtitle="Staff and user activity overview",
    )


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
        from security_suite.security_devices import conf as dev_conf
        from security_suite.security_bots import conf as bot_conf
        from security_suite.security_risk import conf as risk_conf
        from apps.core.models import AppRegistry

        reg = AppRegistry.get_solo()
        security_status.update(
            {
                "devices_enabled": dev_conf.get("PERSISTENCE_ENABLED", True),
                "bots_enabled": bot_conf.get("ENABLED", True),
                "risk_enabled": risk_conf.get("ENABLED", True),
                "login_policy": sec_conf.get("DEFAULT_LOGIN_RISK_POLICY", "mfa_if_high"),
                "ads_enabled": bool(getattr(reg, "ads_enabled", True)),
                "seo_enabled": bool(getattr(reg, "seo_enabled", True)),
                "comments_enabled": bool(getattr(reg, "comments_enabled", True)),
                "distribution_enabled": bool(getattr(reg, "distribution_enabled", True)),
                "device_identity_enabled": bool(getattr(reg, "device_identity_enabled", True)),
                "crawler_guard_enabled": bool(getattr(reg, "crawler_guard_enabled", True)),
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
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Settings", None)),
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
        cache_ttl_seconds = forms.IntegerField(required=False, min_value=60, max_value=86400)

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
def admin_suite_user_detail(request: HttpRequest, user_id: str) -> HttpResponse:
    """User detail view with devices and risk insights."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    from apps.users.services.admin_profile import get_user_profile

    profile = get_user_profile(user_id)
    user_obj = profile.get("user")
    if not user_obj:
        raise Http404("User not found")

    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action in {"toggle_staff", "toggle_active"}:
                field = "is_staff" if action == "toggle_staff" else "is_active"
                current = bool(getattr(user_obj, field))
                setattr(user_obj, field, not current)
                user_obj.save(update_fields=[field])
                message = f"{field} set to {not current}"
                logger.info(
                    "admin_suite_user_toggle",
                    extra={"user_id": str(user_obj.id), "field": field, "staff_user": getattr(request.user, "email", None)},
                )
            elif action == "force_verify_email":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                target_email = request.POST.get("email") or user_obj.email
                from django.utils import timezone

                try:
                    from allauth.account.models import EmailAddress

                    EmailAddress.objects.update_or_create(
                        user=user_obj,
                        email=target_email,
                        defaults={"verified": True, "primary": True},
                    )
                except Exception:
                    pass
                if hasattr(user_obj, "email_verified_at"):
                    user_obj.email_verified_at = timezone.now()
                    user_obj.save(update_fields=["email_verified_at"])
                message = "Email marked as verified."
                logger.info(
                    "admin_suite_user_force_verify",
                    extra={"user_id": str(user_obj.id), "email": target_email, "staff_user": getattr(request.user, "email", None)},
                )
            elif action == "invalidate_sessions":
                try:
                    from django.contrib.sessions.models import Session
                    from django.utils import timezone

                    active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
                    for sess in active_sessions:
                        try:
                            data = sess.get_decoded()
                        except Exception:
                            continue
                        if str(data.get("_auth_user_id")) == str(getattr(user_obj, "id", None)):
                            sess.delete()
                except Exception:
                    pass
                message = "User sessions invalidated."
                logger.info(
                    "admin_suite_user_invalidate_sessions",
                    extra={"user_id": str(user_obj.id), "staff_user": getattr(request.user, "email", None)},
                )
            elif action == "send_password_reset":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                try:
                    from allauth.account.forms import ResetPasswordForm

                    form = ResetPasswordForm(data={"email": user_obj.email})
                    if form.is_valid():
                        form.save(request)
                        message = "Password reset email sent."
                    else:
                        message = "Password reset could not be sent."
                except Exception:
                    message = "Password reset could not be sent."
                logger.info(
                    "admin_suite_user_password_reset",
                    extra={"user_id": str(user_obj.id), "staff_user": getattr(request.user, "email", None)},
                )
            elif action in {"block_device", "unblock_device", "trust_device", "untrust_device"}:
                device_id = request.POST.get("device_id")
                if device_id:
                    from apps.devices.models import Device

                    device = Device.objects.filter(pk=device_id, user=user_obj).first()
                    if device:
                        if action == "block_device":
                            device.is_blocked = True
                        elif action == "unblock_device":
                            device.is_blocked = False
                        elif action == "trust_device":
                            device.is_trusted = True
                        elif action == "untrust_device":
                            device.is_trusted = False
                        device.save(update_fields=["is_blocked", "is_trusted"])
                        message = "Device updated."
                        logger.info(
                            "admin_suite_user_device_action",
                            extra={
                                "user_id": str(user_obj.id),
                                "device_id": str(device_id),
                                "action": action,
                                "staff_user": getattr(request.user, "email", None),
                            },
                        )
            elif action == "reset_device_quota":
                try:
                    from apps.devices.models_quota import UserDeviceQuota

                    quota, _ = UserDeviceQuota.objects.get_or_create(user_id=user_obj.id)
                    quota.last_reset_at = timezone.now()
                    quota.save(update_fields=["last_reset_at"])
                    message = "Device quota reset."
                    logger.info(
                        "admin_suite_user_quota_reset",
                        extra={"user_id": str(user_obj.id), "staff_user": getattr(request.user, "email", None)},
                    )
                except Exception:
                    message = "Quota reset failed."
            elif action == "ban_user":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                user_obj.is_active = False
                user_obj.save(update_fields=["is_active"])
                message = "User banned (set inactive)."
                logger.info(
                    "admin_suite_user_ban",
                    extra={"user_id": str(user_obj.id), "staff_user": getattr(request.user, "email", None)},
                )
            elif action == "delete_user":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                # Soft-delete: deactivate and anonymize identifiers to avoid collisions.
                user_obj.is_active = False
                if hasattr(user_obj, "email") and user_obj.email:
                    ts = timezone.now().strftime("%Y%m%d%H%M%S")
                    user_obj.email = f"deleted+{user_obj.id}+{ts}@example.invalid"
                if hasattr(user_obj, "username"):
                    user_obj.username = f"deleted_{user_obj.id}_{int(timezone.now().timestamp())}"
                user_obj.save()
                message = "User deactivated and anonymized."
                logger.info(
                    "admin_suite_user_delete_soft",
                    extra={"user_id": str(user_obj.id), "staff_user": getattr(request.user, "email", None)},
                )
            elif action == "hard_delete_user":
                if not getattr(request.user, "is_superuser", False):
                    message = "Superuser required for this action."
                    raise Exception("superuser_required")
                uid = str(user_obj.id)
                user_obj.delete()
                logger.info(
                    "admin_suite_user_delete_hard",
                    extra={"user_id": uid, "staff_user": getattr(request.user, "email", None)},
                )
                return HttpResponseRedirect(reverse("admin_suite:admin_suite_users"))
        except Exception as exc:
            logger.warning("Admin suite user action failed: %s", exc)
            message = "Action failed."

    return _render_admin(
        request,
        "admin_suite/user_detail.html",
        {
            "user_obj": user_obj,
            "devices": profile.get("devices", []),
            "device_events": profile.get("device_events", []),
            "risk_insights": profile.get("risk_insights", []),
            "email_addresses": profile.get("email_addresses", []),
            "social_accounts": profile.get("social_accounts", []),
            "message": message,
        },
        nav_active="users",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Users", "admin_suite:admin_suite_users"),
            (getattr(user_obj, "email", "User"), None),
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
            from apps.consent.models import ConsentPolicy
            from django.utils import timezone

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
        from apps.consent.models import ConsentPolicy, ConsentDecision, ConsentEvent
        from django.utils import timezone

        stats["policies_total"] = ConsentPolicy.objects.count()
        stats["policies_active"] = ConsentPolicy.objects.filter(is_active=True).count()

        policies = list(
            ConsentPolicy.objects.order_by("-effective_from")[:10].values(
                "id", "version", "site_domain", "is_active", "effective_from"
            )
        )

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["decisions_24h"] = ConsentDecision.objects.filter(created_at__gte=since).count()
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
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Consent", None)),
        subtitle="Policies, decisions, and banner health",
    )


# ==============================================================================
# Pages (CMS-lite) management
# ==============================================================================


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = [
            "title",
            "slug",
            "status",
            "access_level",
            "include_in_sitemap",
            "changefreq",
            "priority",
            "content_format",
            "content",
            "publish_at",
            "unpublish_at",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "unpublish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "border border-slate-300 rounded px-2 py-1 w-full bg-white text-slate-900"
        for name, field in self.fields.items():
            if name in {"include_in_sitemap"}:
                continue
            classes = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{classes} {base_class}".strip()


@csrf_protect
@staff_member_required
def admin_suite_pages(request: HttpRequest) -> HttpResponse:
    """Full-featured pages management inside Admin Suite."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    edit_page = None

    if request.method == "POST":
        action = request.POST.get("action") or ""
        page_id = request.POST.get("page_id")
        if action in {"publish", "unpublish", "delete"} and page_id:
            page = Page.objects.filter(pk=page_id).first()
            if page:
                if action == "delete":
                    page.delete()
                    message = f"Deleted page {page.slug}."
                elif action == "publish":
                    page.status = "published"
                    page.save(update_fields=["status", "updated_at"])
                    message = f"Published {page.slug}."
                elif action == "unpublish":
                    page.status = "draft"
                    page.save(update_fields=["status", "updated_at"])
                    message = f"Unpublished {page.slug}."
        elif action == "save":
            instance = Page.objects.filter(pk=page_id).first() if page_id else None
            form = PageForm(request.POST, instance=instance)
            if form.is_valid():
                page = form.save(commit=False)
                if instance is None:
                    page.created_by = request.user
                page.updated_by = request.user
                page.save()
                message = f"Saved page {page.slug}."
            else:
                edit_page = instance
                message = "Please correct the errors below."

    if request.method == "GET" and request.GET.get("page_id"):
        edit_page = Page.objects.filter(pk=request.GET.get("page_id")).first()

    form = PageForm(instance=edit_page)

    pages = list(Page.objects.order_by("-updated_at")[:200])
    stats = {
        "total": Page.objects.count(),
        "published": Page.objects.filter(status="published").count(),
        "drafts": Page.objects.filter(status="draft").count(),
        "archived": Page.objects.filter(status="archived").count(),
        "sitemap": Page.objects.filter(include_in_sitemap=True, status="published").count(),
    }

    return _render_admin(
        request,
        "admin_suite/pages.html",
        {
            "pages": pages,
            "form": form,
            "edit_page": edit_page,
            "stats": stats,
            "message": message,
        },
        nav_active="pages",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Pages", None)),
        subtitle="Pages (public) management",
    )


@staff_member_required
def admin_suite_blog(request: HttpRequest) -> HttpResponse:
    """
    Blog management (create/edit/publish) inside Admin Suite to replace legacy Django admin usage.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    try:
        from apps.blog.models import Post, PostStatus, Category
    except Exception:
        raise Http404("Blog module not installed")

    class BlogPostForm(forms.ModelForm):
        class Meta:
            model = Post
            fields = [
                "title",
                "slug",
                "status",
                "publish_at",
                "seo_title",
                "seo_description",
                "canonical_url",
                "summary",
                "body",
                "category",
                "featured",
            ]
            widgets = {
                "publish_at": forms.DateTimeInput(
                    attrs={"type": "datetime-local", "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "summary": forms.Textarea(
                    attrs={"rows": 2, "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "body": forms.Textarea(
                    attrs={"rows": 8, "class": "w-full border rounded px-2 py-2 bg-white text-slate-900"}
                ),
                "title": forms.TextInput(
                    attrs={"class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "slug": forms.TextInput(
                    attrs={"class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "seo_title": forms.TextInput(
                    attrs={"class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "seo_description": forms.Textarea(
                    attrs={"rows": 2, "class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "canonical_url": forms.URLInput(
                    attrs={"class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}
                ),
                "status": forms.Select(attrs={"class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}),
                "category": forms.Select(attrs={"class": "w-full border rounded px-2 py-1 bg-white text-slate-900"}),
                "featured": forms.CheckboxInput(attrs={"class": "h-4 w-4 text-primary"}),
            }

    message = ""
    edit_post = None

    if request.method == "POST":
        action = request.POST.get("action")
        post_id = request.POST.get("post_id")
        if action in {"delete", "publish", "unpublish"} and post_id:
            try:
                target = Post.objects.get(pk=post_id)
                if action == "delete":
                    target.delete()
                    message = "Post deleted."
                elif action == "publish":
                    target.status = PostStatus.PUBLISHED
                    target.save()
                    message = "Post published."
                elif action == "unpublish":
                    target.status = PostStatus.DRAFT
                    target.save()
                    message = "Post moved to draft."
            except Exception as exc:
                message = f"Action failed: {exc}"
        elif action == "save":
            instance = Post.objects.filter(pk=post_id).first() if post_id else None
            form = BlogPostForm(request.POST, instance=instance)
            if form.is_valid():
                post = form.save(commit=False)
                if not post.author_id:
                    post.author = getattr(request, "user", None)
                post.save()
                form.save_m2m()
                message = "Post saved."
                edit_post = post
            else:
                edit_post = instance
        return redirect(f"{reverse('admin_suite:admin_suite_blog')}?message={message}")

    if request.method == "GET" and request.GET.get("post_id"):
        edit_post = Post.objects.filter(pk=request.GET.get("post_id")).first()
    form = BlogPostForm(instance=edit_post)
    if request.GET.get("message"):
        message = request.GET.get("message")

    posts = list(Post.objects.order_by("-updated_at")[:200])
    stats = {
        "total": Post.objects.count(),
        "published": Post.objects.filter(status=PostStatus.PUBLISHED).count(),
        "drafts": Post.objects.filter(status=PostStatus.DRAFT).count(),
        "scheduled": Post.objects.filter(status=PostStatus.SCHEDULED).count(),
        "archived": Post.objects.filter(status=PostStatus.ARCHIVED).count(),
    }

    # SEO helper: suggested tags and health capsule for the edit target
    suggested_tags = []
    seo_health = {}
    if edit_post:
        try:
            from apps.seo.auto import suggest_tags, ensure_canonical

            suggested_tags = suggest_tags([edit_post.title, edit_post.summary or "", edit_post.body], max_tags=6)
            seo_health = {
                "title_len": len(edit_post.title or ""),
                "desc_len": len((edit_post.seo_description or edit_post.summary or "")),
                "word_count": len((edit_post.body or "").split()),
                "tag_count": edit_post.tags.count(),
                "canonical": ensure_canonical(edit_post) or "",
            }
        except Exception:
            suggested_tags = []
            seo_health = {}

    return _render_admin(
        request,
        "admin_suite/blog.html",
        {
            "posts": posts,
            "form": form,
            "edit_post": edit_post,
            "message": message,
            "categories": Category.objects.all()[:100],
            "stats": stats,
            "suggested_tags": suggested_tags,
            "seo_health": seo_health,
        },
        nav_active="blog",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Blog", None)),
        subtitle="Blog posts management",
    )


@staff_member_required
def admin_suite_content(request: HttpRequest) -> HttpResponse:
    """Content/SEO overview (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "posts_total": 0,
        "posts_published": 0,
        "posts_draft": 0,
        "comments_pending": 0,
        "comments_spam": 0,
    }
    posts: list[Dict[str, Any]] = []
    comments: list[Dict[str, Any]] = []

    try:
        from apps.blog.models import Post, PostStatus

        stats["posts_total"] = Post.objects.count()
        stats["posts_published"] = Post.objects.filter(status=PostStatus.PUBLISHED).count()
        stats["posts_draft"] = Post.objects.filter(status=PostStatus.DRAFT).count()
        posts = list(
            Post.objects.filter(status=PostStatus.PUBLISHED)
            .order_by("-published_at")[:10]
            .values("title", "slug", "published_at", "author_id")
        )
    except Exception as exc:
        logger.debug("Admin suite content posts snapshot failed: %s", exc)

    try:
        from apps.comments.models import Comment

        stats["comments_pending"] = Comment.objects.filter(status=Comment.Status.PENDING).count()
        stats["comments_spam"] = Comment.objects.filter(status=Comment.Status.SPAM).count()
        comments = list(
            Comment.objects.filter(status=Comment.Status.PENDING)
            .order_by("-created_at")[:10]
            .values("id", "user_id", "body", "created_at", "post_id")
        )
    except Exception as exc:
        logger.debug("Admin suite content comments snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/content.html",
        {
            "stats": stats,
            "posts": posts,
            "comments": comments,
        },
        nav_active="content",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Content", None)),
        subtitle="Posts, comments, and moderation status",
    )


@staff_member_required
def admin_suite_marketing(request: HttpRequest) -> HttpResponse:
    """Ads + SEO overview (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "placements": 0,
        "creatives": 0,
        "impressions_24h": 0,
        "clicks_24h": 0,
        "redirects": 0,
        "sitemap_urls": 0,
    }
    placements: list[Dict[str, Any]] = []
    redirects: list[Dict[str, Any]] = []

    # Ads snapshot
    try:
        from apps.ads.models import AdPlacement, AdCreative, AdEvent
        from django.utils import timezone

        stats["placements"] = AdPlacement.objects.count()
        stats["creatives"] = AdCreative.objects.count()
        since = timezone.now() - timezone.timedelta(hours=24)
        stats["impressions_24h"] = AdEvent.objects.filter(
            event_type="impression", created_at__gte=since
        ).count()
        stats["clicks_24h"] = AdEvent.objects.filter(
            event_type="click", created_at__gte=since
        ).count()
        placements = list(
            AdPlacement.objects.order_by("-updated_at")[:10].values(
                "name", "slug", "page_context", "updated_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite ads snapshot failed: %s", exc)

    # SEO snapshot
    try:
        from apps.seo.models import Redirect, SitemapEntry

        stats["redirects"] = Redirect.objects.count()
        stats["sitemap_urls"] = SitemapEntry.objects.count()
        redirects = list(
            Redirect.objects.order_by("-updated_at")[:10].values(
                "source", "target", "is_permanent", "updated_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite seo snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/marketing.html",
        {
            "stats": stats,
            "placements": placements,
            "redirects": redirects,
        },
        nav_active="marketing",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Marketing", None)),
        subtitle="Ads and SEO snapshots",
    )


@staff_member_required
def admin_suite_distribution(request: HttpRequest) -> HttpResponse:
    """Distribution overview."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "accounts": 0,
        "plans": 0,
        "jobs_pending": 0,
        "jobs_failed": 0,
        "logs_24h": 0,
    }
    accounts: list[Dict[str, Any]] = []
    plans: list[Dict[str, Any]] = []
    jobs: list[Dict[str, Any]] = []
    logs: list[Dict[str, Any]] = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 10
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(50, int(request.GET.get("page_size", "10"))))
    except Exception:
        page = 1
        page_size = 10
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.distribution.models import SocialAccount, SharePlan, ShareJob

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
                fields = {
                    "channel": (request.POST.get("channel") or "")[:50],
                    "account_name": (request.POST.get("account_name") or "")[:255],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if aid:
                    SocialAccount.objects.filter(pk=aid).update(**fields)
                else:
                    SocialAccount.objects.create(**fields)
                message = "Account saved."
            elif action == "save_plan":
                pid = request.POST.get("plan_id")
                fields = {
                    "name": (request.POST.get("name") or "")[:255],
                    "description": (request.POST.get("description") or "")[:500],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if pid:
                    SharePlan.objects.filter(pk=pid).update(**fields)
                else:
                    SharePlan.objects.create(**fields)
                message = "Plan saved."
            elif action == "retry_job":
                jid = request.POST.get("job_id")
                ShareJob.objects.filter(pk=jid).update(status="pending", last_error="")
                message = "Job retried."
            elif action == "delete_job":
                jid = request.POST.get("job_id")
                ShareJob.objects.filter(pk=jid).delete()
                message = "Job deleted."
        except Exception as exc:
            logger.warning("Admin suite distribution toggle failed: %s", exc)
            message = "Action failed."

    try:
        from apps.distribution.models import SocialAccount, SharePlan, ShareJob, ShareLog
        from django.utils import timezone

        stats["accounts"] = SocialAccount.objects.count()
        stats["plans"] = SharePlan.objects.count()
        stats["jobs_pending"] = ShareJob.objects.filter(status="pending").count()
        stats["jobs_failed"] = ShareJob.objects.filter(status="failed").count()

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["logs_24h"] = ShareLog.objects.filter(created_at__gte=since).count()

        account_qs = SocialAccount.objects.order_by("channel", "account_name")
        plan_qs = SharePlan.objects.order_by("-created_at")
        if query:
            from django.db.models import Q

            account_qs = account_qs.filter(Q(channel__icontains=query) | Q(account_name__icontains=query))
            plan_qs = plan_qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
            jobs_qs = ShareJob.objects.order_by("-created_at").filter(
                Q(channel__icontains=query) | Q(status__icontains=query)
            )
            logs_qs = ShareLog.objects.order_by("-created_at").filter(Q(level__icontains=query) | Q(message__icontains=query))
        else:
            jobs_qs = ShareJob.objects.order_by("-created_at")
            logs_qs = ShareLog.objects.order_by("-created_at")

        accounts = list(
            account_qs[:20].values(
                "id", "channel", "account_name", "is_active", "token_expires_at"
            )
        )
        plans = list(
            plan_qs[:20].values("id", "name", "description", "is_active", "created_at")
        )
        jobs = list(
            jobs_qs[offset : offset + page_size].values(
                "id", "channel", "status", "created_at", "attempt_count", "last_error"
            )
        )
        logs = list(
            logs_qs[offset : offset + page_size].values(
                "job_id", "level", "message", "created_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite distribution snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/distribution.html",
        {
            "stats": stats,
            "accounts": accounts,
            "plans": plans,
            "jobs": jobs,
            "logs": logs,
            "message": message,
            "q": query,
            "page": page,
            "page_size": page_size,
        },
        nav_active="distribution",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("Distribution", None)),
        subtitle="Accounts, plans, jobs, and logs",
    )


@staff_member_required
def admin_suite_ads(request: HttpRequest) -> HttpResponse:
    """Ads read-only dashboard: placements, creatives, events stats."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "placements": 0,
        "creatives": 0,
        "impressions_24h": 0,
        "clicks_24h": 0,
    }
    placements: list[Dict[str, Any]] = []
    creatives: list[Dict[str, Any]] = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 20
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(50, int(request.GET.get("page_size", "20"))))
    except Exception:
        page = 1
        page_size = 20
    offset = (page - 1) * page_size
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ads.models import AdPlacement, AdCreative

            if action == "disable_placement":
                pid = request.POST.get("placement_id")
                AdPlacement.objects.filter(pk=pid).update(is_active=False)
            elif action == "enable_placement":
                pid = request.POST.get("placement_id")
                AdPlacement.objects.filter(pk=pid).update(is_active=True)
            elif action == "disable_creative":
                cid = request.POST.get("creative_id")
                AdCreative.objects.filter(pk=cid).update(is_active=False)
            elif action == "enable_creative":
                cid = request.POST.get("creative_id")
                AdCreative.objects.filter(pk=cid).update(is_active=True)
            elif action == "save_placement":
                pid = request.POST.get("placement_id")
                fields = {
                    "name": (request.POST.get("name") or "")[:255],
                    "slug": (request.POST.get("slug") or "")[:255],
                    "page_context": (request.POST.get("page_context") or "")[:255],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if pid:
                    AdPlacement.objects.filter(pk=pid).update(**fields)
                else:
                    AdPlacement.objects.create(**fields)
                message = "Placement saved."
            elif action == "save_creative":
                cid = request.POST.get("creative_id")
                fields = {
                    "name": (request.POST.get("name") or "")[:255],
                    "creative_type": (request.POST.get("creative_type") or "")[:64],
                    "is_active": bool(request.POST.get("is_active")),
                }
                if cid:
                    AdCreative.objects.filter(pk=cid).update(**fields)
                else:
                    AdCreative.objects.create(**fields)
                message = "Creative saved."
        except Exception as exc:
            logger.warning("Admin suite ads toggle/save failed: %s", exc)
            message = "Action failed."

    try:
        from apps.ads.models import AdPlacement, AdCreative, AdEvent
        from django.utils import timezone

        stats["placements"] = AdPlacement.objects.count()
        stats["creatives"] = AdCreative.objects.count()
        since = timezone.now() - timezone.timedelta(hours=24)
        stats["impressions_24h"] = AdEvent.objects.filter(
            event_type="impression", created_at__gte=since
        ).count()
        stats["clicks_24h"] = AdEvent.objects.filter(
            event_type="click", created_at__gte=since
        ).count()

        placement_qs = AdPlacement.objects.order_by("-updated_at")
        creative_qs = AdCreative.objects.order_by("-updated_at")
        if query:
            from django.db.models import Q

            placement_qs = placement_qs.filter(
                Q(name__icontains=query) | Q(slug__icontains=query) | Q(page_context__icontains=query)
            )
            creative_qs = creative_qs.filter(
                Q(name__icontains=query) | Q(creative_type__icontains=query)
            )

        placements = list(
            placement_qs[offset : offset + page_size].values(
                "id", "name", "slug", "page_context", "is_active", "updated_at"
            )
        )
        creatives = list(
            creative_qs[offset : offset + page_size].values(
                "id", "name", "creative_type", "is_active", "updated_at"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite ads snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ads.html",
        {
            "stats": stats,
            "placements": placements,
            "creatives": creatives,
            "message": message,
            "q": query,
            "page": page,
            "page_size": page_size,
        },
        nav_active="ads",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Marketing", "admin_suite:admin_suite_marketing"),
            ("Ads", None),
        ),
        subtitle="Placements, creatives, and 24h activity",
    )


@staff_member_required
def admin_suite_tags(request: HttpRequest) -> HttpResponse:
    """Tags read-only dashboard."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {"total": 0, "curated": 0, "deleted": 0}
    tags: list[Dict[str, Any]] = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 25
    if request.GET.get("refresh"):
        message = "Sitemap snapshot refreshed."
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            import bleach
            from apps.tags.models import Tag

            name = bleach.clean(request.POST.get("name", ""), strip=True)
            if action == "create" and name:
                Tag.objects.create(name=name)
                message = "Tag created."
            elif action == "update":
                tid = request.POST.get("tag_id")
                if tid and name:
                    Tag.objects.filter(pk=tid).update(name=name)
                    message = "Tag updated."
            elif action == "delete":
                tid = request.POST.get("tag_id")
                if tid:
                    Tag.objects.filter(pk=tid).update(is_deleted=True)
                    message = "Tag deleted."
        except Exception as exc:
            logger.warning("Admin suite tags action failed: %s", exc)
            message = "Action failed."

    try:
        from apps.tags.models import Tag

        stats["total"] = Tag.objects.count()
        stats["curated"] = Tag.objects.filter(is_curated=True).count()
        stats["deleted"] = Tag.objects.filter(is_deleted=True).count()
        qs = Tag.objects.filter(is_deleted=False).order_by("-usage_count", "name")
        if query:
            from django.db.models import Q

            qs = qs.filter(Q(name__icontains=query) | Q(slug__icontains=query))
        tags = list(
            qs[offset : offset + page_size].values("id", "name", "slug", "usage_count", "is_curated")
        )
    except Exception as exc:
        logger.debug("Admin suite tags snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/tags.html",
        {
            "stats": stats,
            "tags": tags,
            "message": message,
            "page": page,
            "page_size": page_size,
            "q": query,
        },
        nav_active="tags",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Content", "admin_suite:admin_suite_content"),
            ("Tags", None),
        ),
        subtitle="Tag usage and curation status",
    )


@staff_member_required
def admin_suite_seo(request: HttpRequest) -> HttpResponse:
    """SEO dashboard: redirects and sitemap entries (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {"redirects": 0, "sitemap_urls": 0}
    redirects: list[Dict[str, Any]] = []
    sitemap_entries: list[Dict[str, Any]] = []
    seo_settings: Dict[str, Any] = {}
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = 1
    page_size = 25
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.seo.models import Redirect, SitemapEntry
            from apps.seo.models_settings import SeoAutomationSettings

            if action == "disable_redirect":
                rid = request.POST.get("redirect_id")
                Redirect.objects.filter(pk=rid).update(is_active=False)
            elif action == "enable_redirect":
                rid = request.POST.get("redirect_id")
                Redirect.objects.filter(pk=rid).update(is_active=True)
            elif action == "disable_sitemap":
                sid = request.POST.get("sitemap_id")
                SitemapEntry.objects.filter(pk=sid).update(is_active=False)
            elif action == "enable_sitemap":
                sid = request.POST.get("sitemap_id")
                SitemapEntry.objects.filter(pk=sid).update(is_active=True)
            elif action == "save_redirect":
                rid = request.POST.get("redirect_id")
                data = {
                    "source": (request.POST.get("source") or "")[:255],
                    "target": (request.POST.get("target") or "")[:255],
                    "is_permanent": bool(request.POST.get("is_permanent")),
                    "is_active": bool(request.POST.get("is_active")),
                }
                if rid:
                    Redirect.objects.filter(pk=rid).update(**data)
                else:
                    Redirect.objects.create(**data)
                message = "Redirect saved."
            elif action == "save_seo_settings":
                cfg = SeoAutomationSettings.get_solo()
                bool_fields = [
                    "auto_meta",
                    "auto_tags",
                    "auto_schema",
                    "suggest_only",
                    "tag_sitemap_enabled",
                    "comment_nofollow",
                    "comment_bump_lastmod",
                ]
                for field in bool_fields:
                    setattr(cfg, field, bool(request.POST.get(field)))
                cfg.save()
                message = "SEO automation settings saved."
            # sitemap entries are auto-fed; no manual save in admin
        except Exception as exc:
            logger.warning("Admin suite seo toggle failed: %s", exc)
            message = "Action failed."

    try:
        from apps.seo.models import Redirect, SitemapEntry
        from apps.seo.models_settings import SeoAutomationSettings

        stats["redirects"] = Redirect.objects.count()
        stats["sitemap_urls"] = SitemapEntry.objects.count()
        redirect_qs = Redirect.objects.order_by("-updated_at")
        sitemap_qs = SitemapEntry.objects.order_by("-created_at")
        if query:
            from django.db.models import Q

            redirect_qs = redirect_qs.filter(Q(source__icontains=query) | Q(target__icontains=query))
            sitemap_qs = sitemap_qs.filter(Q(url__icontains=query) | Q(changefreq__icontains=query))

        redirects = list(
            redirect_qs[offset : offset + page_size].values(
                "id", "source", "target", "is_permanent", "is_active", "updated_at"
            )
        )
        sitemap_entries = list(
            sitemap_qs[offset : offset + page_size].values(
                "id", "url", "lastmod", "changefreq", "priority", "is_active"
            )
        )
        try:
            cfg = SeoAutomationSettings.get_solo()
            seo_settings = {
                "auto_meta": bool(getattr(cfg, "auto_meta", True)),
                "auto_tags": bool(getattr(cfg, "auto_tags", True)),
                "auto_schema": bool(getattr(cfg, "auto_schema", True)),
                "suggest_only": bool(getattr(cfg, "suggest_only", False)),
                "tag_sitemap_enabled": bool(getattr(cfg, "tag_sitemap_enabled", True)),
                "comment_nofollow": bool(getattr(cfg, "comment_nofollow", True)),
                "comment_bump_lastmod": bool(getattr(cfg, "comment_bump_lastmod", True)),
            }
        except Exception:
            seo_settings = {}
    except Exception as exc:
        logger.debug("Admin suite seo snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/seo.html",
        {
            "stats": stats,
            "redirects": redirects,
            "sitemap_entries": sitemap_entries,
            "seo_settings": seo_settings,
            "message": message,
            "q": query,
            "page": page,
            "page_size": page_size,
        },
        nav_active="seo",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Marketing", "admin_suite:admin_suite_marketing"),
            ("SEO", None),
        ),
        subtitle="Redirects and sitemap entries",
    )


@staff_member_required
def admin_suite_registry(request: HttpRequest) -> HttpResponse:
    """App registry flags (read-only)."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    registry = {}
    try:
        from apps.core.models import AppRegistry

        reg = AppRegistry.get_solo()
        registry = reg.__dict__.copy()
        registry = {k: v for k, v in registry.items() if not k.startswith("_")}
    except Exception as exc:
        logger.debug("Admin suite app registry snapshot failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/registry.html",
        {
            "registry": registry,
        },
        nav_active="registry",
        breadcrumb=_make_breadcrumb(("Admin Home", "admin_suite:admin_suite"), ("App Registry", None)),
        subtitle="App flags and feature registry (read-only snapshot)",
    )


@csrf_protect
@staff_member_required
def admin_suite_comments(request: HttpRequest) -> HttpResponse:
    """
    Comment moderation (staff-only). Supports POST actions: approve, reject, spam.
    """
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    action = request.POST.get("action") if request.method == "POST" else ""
    comment_id = request.POST.get("comment_id") if request.method == "POST" else None

    if request.method == "POST" and comment_id and action in {"approve", "reject", "spam"}:
        try:
            from apps.comments.models import Comment

            comment = Comment.objects.filter(pk=comment_id).first()
            if comment:
                if action == "approve":
                    comment.status = Comment.Status.APPROVED
                    comment.is_approved = True
                elif action == "reject":
                    comment.status = Comment.Status.REJECTED
                    comment.is_approved = False
                elif action == "spam":
                    comment.status = Comment.Status.SPAM
                    comment.is_approved = False
                comment.save(update_fields=["status", "is_approved"])
                message = f"Comment {comment_id} marked as {action}."
                logger.info(
                    "admin_suite_comment_action",
                    extra={
                        "comment_id": comment_id,
                        "action": action,
                        "staff_user": getattr(request.user, "email", None),
                    },
                )
        except Exception as exc:
            logger.warning("Admin suite comment action failed: %s", exc)
            message = "Action failed."

    pending_comments: list[Dict[str, Any]] = []
    page = 1
    page_size = 25
    try:
        page = max(1, int(request.GET.get("page", "1")))
        page_size = max(1, min(100, int(request.GET.get("page_size", "25"))))
    except Exception:
        page = 1
        page_size = 25

    try:
        from apps.comments.models import Comment

        offset = (page - 1) * page_size
        qs = Comment.objects.filter(status=Comment.Status.PENDING).order_by("-created_at")
        pending_comments = list(
            qs[offset : offset + page_size].values(
                "id", "user_id", "body", "created_at", "post_id"
            )
        )
    except Exception as exc:
        logger.debug("Admin suite pending comments fetch failed: %s", exc)

    return _render_admin(
        request,
        "admin_suite/comments.html",
        {
            "pending_comments": pending_comments,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="comments",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Content", "admin_suite:admin_suite_content"),
            ("Comments", None),
        ),
        subtitle="Moderate pending comments",
    )
