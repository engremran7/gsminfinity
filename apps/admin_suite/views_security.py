from __future__ import annotations

from django.utils import timezone


from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_protect

from .views_shared import STAFF_ONLY, _ADMIN_DISABLED, _make_breadcrumb, _render_admin
# Explicitly import underscore-prefixed helpers that star import omits
from .views_shared import _ADMIN_DISABLED, _make_breadcrumb, _render_admin

__all__ = [
    "admin_suite_command_search",
    "admin_suite",
    "admin_suite_security",
    "admin_suite_security_devices",
    "admin_suite_security_crawlers",
    "admin_suite_security_risk",
    "_render_admin",
    "_make_breadcrumb",
    "_ADMIN_DISABLED",
]


# Extracted views_security views from legacy views.py
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
        (
            "Distribution",
            "admin_suite:admin_suite_distribution",
            "distribution syndication",
        ),
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
                "login_policy": sec_conf.get(
                    "DEFAULT_LOGIN_RISK_POLICY", "mfa_if_high"
                ),
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
                ("delete", "delete"),
            ]
        )
        device_id = forms.CharField(required=False)
        user_id = forms.IntegerField(required=False)

    class CrawlerRuleForm(forms.Form):
        action = forms.ChoiceField(
            choices=[("enable", "enable"), ("disable", "disable"), ("create", "create")]
        )
        rule_id = forms.CharField(required=False)
        name = forms.CharField(required=False, max_length=100)
        path_pattern = forms.RegexField(
            required=False, regex=r"^[\\w./*-]+$", max_length=255
        )
        requests_per_minute = forms.IntegerField(
            required=False, min_value=1, max_value=6000
        )

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
            if insight_id and new_status in {
                "open",
                "approved",
                "rejected",
                "resolved",
            }:
                try:
                    from apps.ai_behavior.models import BehaviorInsight

                    insight = BehaviorInsight.objects.filter(pk=insight_id).first()
                    if insight:
                        insight.status = new_status
                        insight.save(update_fields=["status"])
                        message = f"Insight {insight_id} set to {new_status}."
                        logger.info(
                            "admin_suite_risk_insight",
                            extra={
                                "insight_id": insight_id,
                                "status": new_status,
                                "staff_user": getattr(request.user, "email", None),
                            },
                        )
                except Exception as exc:
                    logger.warning("Admin suite risk action failed: %s", exc)
                    message = "Action failed."
        elif action in {
            "block",
            "unblock",
            "trust",
            "untrust",
            "reset_quota",
            "delete",
        }:
            try:
                form = DeviceActionForm(request.POST)
                if form.is_valid():
                    cleaned = form.cleaned_data
                    device_id = cleaned.get("device_id")
                    user_id = cleaned.get("user_id")
                    from apps.devices.models import Device
                    from apps.devices.models_quota import UserDeviceQuota

                    if action == "reset_quota" and user_id:
                        quota, _ = UserDeviceQuota.objects.get_or_create(
                            user_id=user_id
                        )
                        quota.last_reset_at = timezone.now()
                        quota.save(update_fields=["last_reset_at"])
                        # Also delete all devices for this user to zero-out footprint
                        deleted, _ = Device.objects.filter(user_id=user_id).delete()
                        message = f"Quota reset and {deleted} device(s) deleted for user {user_id}."
                        logger.info(
                            "admin_suite_device_quota_reset",
                            extra={
                                "user_id": str(user_id),
                                "action": action,
                                "deleted": deleted,
                                "staff_user": getattr(request.user, "email", None),
                            },
                        )
                        return redirect(f"{request.path}#devices")
                    elif action == "reset_quota" and not user_id:
                        message = "Select a user to reset quota."
                        return redirect(f"{request.path}#devices")
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
                            elif action == "delete":
                                device.delete()
                                message = f"Device {device_id} deleted."
                                logger.info(
                                    "admin_suite_device_delete",
                                    extra={
                                        "device_id": str(device_id),
                                        "action": action,
                                        "staff_user": getattr(
                                            request.user, "email", None
                                        ),
                                    },
                                )
                                return redirect(f"{request.path}#devices")
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
                            return redirect(f"{request.path}#devices")
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

                if flag in {
                    "device_identity_enabled",
                    "crawler_guard_enabled",
                    "ai_behavior_enabled",
                }:
                    reg = AppRegistry.get_solo()
                    current = bool(getattr(reg, flag))
                    setattr(reg, flag, not current)
                    reg.save(update_fields=[flag])
                    registry_flags[flag] = not current
                    message = f"{flag} set to {not current}"
                    logger.info(
                        "admin_suite_security_toggle_flag",
                        extra={
                            "flag": flag,
                            "value": not current,
                            "staff_user": getattr(request.user, "email", None),
                        },
                    )
            except Exception as exc:
                logger.warning("Admin suite security toggle failed: %s", exc)
                message = "Toggle failed."
        elif action == "update_security_config":
            try:
                from apps.security_suite.models import SecurityConfig

                cfg = SecurityConfig.get_solo()
                cfg.devices_enabled = bool(request.POST.get("devices_enabled"))
                cfg.crawler_guard_enabled = bool(
                    request.POST.get("crawler_guard_enabled")
                )
                cfg.mfa_enabled = bool(request.POST.get("mfa_enabled"))
                cfg.login_risk_enabled = bool(request.POST.get("login_risk_enabled"))
                cfg.device_quota_enforcement_enabled = bool(
                    request.POST.get("device_quota_enforcement_enabled")
                )
                try:
                    cfg.default_device_limit = max(
                        1,
                        int(
                            request.POST.get("default_device_limit")
                            or cfg.default_device_limit
                        ),
                    )
                except Exception:
                    pass
                window = (
                    request.POST.get("default_device_window")
                    or cfg.default_device_window
                )
                if window in {"3m", "6m", "12m"}:
                    cfg.default_device_window = window
                c_action = (
                    request.POST.get("crawler_default_action")
                    or cfg.crawler_default_action
                )
                if c_action in {"allow", "throttle", "block", "challenge"}:
                    cfg.crawler_default_action = c_action
                tier = request.POST.get("security_tier") or cfg.security_tier
                if tier in {"basic", "standard", "strict"}:
                    cfg.security_tier = tier
                mfa_policy = request.POST.get("mfa_policy") or cfg.mfa_policy
                if mfa_policy in {"optional", "mfa_if_high", "required"}:
                    cfg.mfa_policy = mfa_policy
                risk_policy = (
                    request.POST.get("login_risk_policy") or cfg.login_risk_policy
                )
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
                cfg.basic_fingerprinting_enabled = bool(
                    request.POST.get("basic_fingerprinting_enabled")
                )
                cfg.enhanced_fingerprinting_enabled = bool(
                    request.POST.get("enhanced_fingerprinting_enabled")
                )
                cfg.enterprise_device_management_enabled = bool(
                    request.POST.get("enterprise_device_management_enabled")
                )
                cfg.strict_new_device_login = bool(
                    request.POST.get("strict_new_device_login")
                )
                cfg.require_mfa_on_new_device = bool(
                    request.POST.get("require_mfa_on_new_device")
                )
                try:
                    cfg.max_devices_default = max(
                        1,
                        int(
                            request.POST.get("max_devices_default")
                            or cfg.max_devices_default
                        ),
                    )
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
                try:
                    expiry = request.POST.get("device_expiry_days")
                    cfg.device_expiry_days = (
                        int(expiry) if expiry not in {None, ""} else None
                    )
                except Exception:
                    pass
                try:
                    cfg.risk_mfa_threshold = max(
                        0,
                        int(
                            request.POST.get("risk_mfa_threshold")
                            or cfg.risk_mfa_threshold
                            or 75
                        ),
                    )
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
    device_window_choices = [
        ("3m", "3 Months"),
        ("6m", "6 Months"),
        ("12m", "12 Months"),
    ]
    security_tier_choices = [
        ("basic", "Basic"),
        ("standard", "Standard"),
        ("strict", "Strict"),
    ]
    mfa_policy_choices = [
        ("optional", "Optional"),
        ("mfa_if_high", "MFA if High"),
        ("required", "Required"),
    ]
    login_risk_policy_choices = [
        ("none", "None"),
        ("info", "Info Only"),
        ("mfa_if_high", "MFA if High"),
        ("block_if_high", "Block if High"),
    ]
    crawler_action_choices = [
        ("allow", "Allow"),
        ("throttle", "Throttle"),
        ("block", "Block"),
        ("challenge", "Challenge"),
    ]

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
            .order_by("-created_at")[:20]
            .values(
                "event_type",
                "success",
                "reason",
                "created_at",
                "device_id",
                "user_id",
                "ip",
                "geo_region",
                "metadata",
            )
        )
        devices = list(
            Device.objects.order_by("-last_seen_at").values(
                "id",
                "user_id",
                "os_fingerprint",
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

        since = timezone.now() - timezone.timedelta(hours=24)
        stats["crawler_events_24h"] = CrawlerEvent.objects.filter(
            created_at__gte=since
        ).count()
        crawler_events = list(
            CrawlerEvent.objects.order_by("-created_at")[:10].values(
                "ip", "action_taken", "path", "created_at"
            )
        )
        rules = list(
            CrawlerRule.objects.order_by("-priority", "name").values(
                "id",
                "name",
                "path_pattern",
                "requests_per_minute",
                "action",
                "is_enabled",
                "priority",
            )
        )
    except Exception as exc:
        logger.debug("Admin suite crawler snapshot failed: %s", exc)

    # Risk insights snapshot
    try:
        from apps.ai_behavior.models import BehaviorInsight

        stats["risk_insights_open"] = BehaviorInsight.objects.filter(
            status="open"
        ).count()
        risk_insights = list(
            BehaviorInsight.objects.order_by("-created_at")[:10].values(
                "severity",
                "status",
                "created_at",
                "related_user_id",
                "device_identifier",
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
            "basic_fingerprinting_enabled": bool(
                getattr(cfg, "basic_fingerprinting_enabled", True)
            ),
            "enhanced_fingerprinting_enabled": bool(
                getattr(cfg, "enhanced_fingerprinting_enabled", False)
            ),
            "enterprise_device_management_enabled": bool(
                getattr(cfg, "enterprise_device_management_enabled", False)
            ),
            "strict_new_device_login": bool(
                getattr(cfg, "strict_new_device_login", False)
            ),
            "require_mfa_on_new_device": bool(
                getattr(cfg, "require_mfa_on_new_device", False)
            ),
            "max_devices_default": getattr(cfg, "max_devices_default", 5),
            "monthly_device_quota": getattr(cfg, "monthly_device_quota", None),
            "yearly_device_quota": getattr(cfg, "yearly_device_quota", None),
            "device_expiry_days": getattr(cfg, "device_expiry_days", None),
            "risk_mfa_threshold": getattr(cfg, "risk_mfa_threshold", 75),
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
            "device_quota_enforcement_enabled": bool(
                getattr(cfg, "device_quota_enforcement_enabled", False)
            ),
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
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"), ("Security", None)
        ),
        subtitle="Devices, bots, and AI behavior/risk controls",
    )


@csrf_protect
@staff_member_required
def admin_suite_security_devices(request: HttpRequest) -> HttpResponse:
    """Legacy route: redirect to consolidated security tab with anchor."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED
    return redirect(f"{reverse('admin_suite:security')}#devices")


@csrf_protect
@staff_member_required
def admin_suite_security_crawlers(request: HttpRequest) -> HttpResponse:
    """Legacy route: redirect to consolidated security tab with anchor."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED
    return redirect(f"{reverse('admin_suite:security')}#crawlers")


@csrf_protect
@staff_member_required
def admin_suite_security_risk(request: HttpRequest) -> HttpResponse:
    """Legacy route: redirect to consolidated security tab with anchor."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED
    return redirect(f"{reverse('admin_suite:security')}#risk")


@csrf_protect
@staff_member_required
def admin_suite_security_events(request: HttpRequest) -> HttpResponse:
    """Security events audit log."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    events = []
    try:
        from apps.security_events.models import SecurityEvent

        events = list(
            SecurityEvent.objects.select_related("user")
            .order_by("-created_at")[:100]
            .values(
                "id",
                "event_type",
                "severity",
                "ip_address",
                "user_agent",
                "created_at",
                "user__email",
            )
        )
    except Exception as exc:
        logger.warning("Failed to load security events: %s", exc)

    return _render_admin(
        request,
        "admin_suite/security_events.html",
        {"events": events},
        nav_active="security",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Security", "admin_suite:security"),
            ("Events", None),
        ),
        subtitle="Security event audit log",
    )


__all__ = [
    "admin_suite_command_search",
    "admin_suite",
    "admin_suite_security",
    "admin_suite_security_devices",
    "admin_suite_security_crawlers",
    "admin_suite_security_risk",
    "admin_suite_security_events",
]
