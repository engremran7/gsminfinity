# apps/core/views.py
from django.shortcuts import render
from django.core.cache import cache
from apps.site_settings.models import SiteSettings, TenantSiteSettings


# ============================================================
#  INTERNAL UTILITY — GLOBAL SETTINGS RESOLVER
# ============================================================
def _get_site_settings():
    """
    Retrieve the global SiteSettings object with caching and fallback safety.

    Features:
    - Cached for 5 minutes (configurable).
    - Safe fallback to dummy defaults when DB not initialized.
    - Prevents repeated DB hits per request.
    """
    cache_key = "global_site_settings"
    site_settings = cache.get(cache_key)
    if site_settings:
        return site_settings

    try:
        # Solo manager preferred
        if hasattr(SiteSettings, "get_solo"):
            site_settings = SiteSettings.get_solo()
        else:
            site_settings = SiteSettings.objects.first()

        cache.set(cache_key, site_settings, timeout=300)
        return site_settings

    except Exception:
        # Fallback Dummy (pre-migrate / debug environments)
        class DummySettings:
            site_name = "GSMInfinity"
            site_header = "GSM Admin"
            site_description = "Default configuration"
            enable_signup = True
            recaptcha_enabled = False
            require_mfa = False
            maintenance_mode = False
            primary_color = "#0d6efd"
            secondary_color = "#6c757d"

        dummy = DummySettings()
        cache.set(cache_key, dummy, timeout=60)
        return dummy


# ============================================================
#  PUBLIC HOME VIEW
# ============================================================
def home(request):
    """
    Display the landing dashboard (system KPIs + branding context).
    Placeholder KPIs can be replaced by live metrics or async APIs.
    """
    s = _get_site_settings()
    context = {
        "site_settings": s,
        "active_users": 1245,
        "mfa_adoption": "87%",
        "revenue": "$12,340",
    }
    return render(request, "core/home.html", context)


# ============================================================
#  DASHBOARD SECTIONS (OVERVIEW / SECURITY / ETC.)
# ============================================================
def overview(request):
    """System overview dashboard page."""
    return render(request, "dashboard/overview.html", {"site_settings": _get_site_settings()})


def security(request):
    """Security metrics dashboard (MFA, auth logs, suspicious activity)."""
    return render(request, "dashboard/security.html", {"site_settings": _get_site_settings()})


def monetization(request):
    """Revenue, plans, and payment analytics dashboard."""
    return render(request, "dashboard/monetization.html", {"site_settings": _get_site_settings()})


def notifications(request):
    """System alerts, notifications, and message center."""
    return render(request, "dashboard/notifications.html", {"site_settings": _get_site_settings()})


def announcements(request):
    """Public changelog and administrative announcements."""
    return render(request, "dashboard/announcements.html", {"site_settings": _get_site_settings()})


def users_dashboard(request):
    """User management and behavioral analytics dashboard."""
    return render(request, "dashboard/users.html", {"site_settings": _get_site_settings()})


def system_health(request):
    """System health, uptime, and diagnostic dashboard."""
    return render(request, "dashboard/system_health.html", {"site_settings": _get_site_settings()})


# ============================================================
#  TENANT MANAGEMENT VIEW
# ============================================================
def tenants(request):
    """
    Render a list of tenant configurations with prefetch optimizations.
    Supports multi-tenant environments sharing the same backend.
    """
    s = _get_site_settings()
    tenants_qs = (
        TenantSiteSettings.objects.select_related("site")
        .prefetch_related("meta_tags", "verification_files")
        .order_by("site__domain")
    )
    return render(
        request,
        "core/tenants.html",
        {"site_settings": s, "tenants": tenants_qs},
    )


# ============================================================
#  CUSTOM ERROR HANDLERS (404 / 403 / 500)
# ============================================================
def error_404_view(request, exception):
    """Custom 404 Not Found handler with branding context."""
    return render(
        request,
        "errors/404.html",
        {"site_settings": _get_site_settings()},
        status=404,
    )


def error_403_view(request, exception):
    """Custom 403 Forbidden handler (permissions)."""
    return render(
        request,
        "errors/403.html",
        {"site_settings": _get_site_settings()},
        status=403,
    )


def error_500_view(request):
    """Custom 500 Internal Server Error handler."""
    return render(
        request,
        "errors/500.html",
        {"site_settings": _get_site_settings()},
        status=500,
    )
