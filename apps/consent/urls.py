from __future__ import annotations

from django.urls import path
from . import views

# If you have a lazy loader utility, import it here.
# Otherwise, implement with django.utils.module_loading.import_string.
try:
    from gsminfinity.urls import lazy_view
except ImportError:
    from django.utils.module_loading import import_string

    def lazy_view(dotted_path: str):
        def _wrapped(*args, **kwargs):
            view = import_string(dotted_path)
            return view(*args, **kwargs)
        return _wrapped

app_name = "consent"

urlpatterns = [
    # ------------------------------------------------------------------
    # Banner loader (HTML partial — HTMX / JS)
    # ------------------------------------------------------------------
    path("banner/", views.banner_partial, name="banner"),

    # ------------------------------------------------------------------
    # Canonical HTML endpoints (UI-driven)
    # ------------------------------------------------------------------
    path("manage/", views.manage_consent, name="manage"),
    path("status/", views.consent_status, name="status"),

    # ------------------------------------------------------------------
    # Consent mutation handlers (HTML/HTMX + JSON fallback)
    # ------------------------------------------------------------------
    path("accept/", views.consent_accept, name="accept"),
    path("accept-all/", views.consent_accept_all, name="accept_all"),
    path("reject-all/", views.consent_reject_all, name="reject_all"),

    # ------------------------------------------------------------------
    # Compatibility aliases (underscore style)
    # Required because frontend still calls /consent/accept_all/ etc.
    # ------------------------------------------------------------------
    path("accept_all/", views.consent_accept_all, name="accept_all_alias"),
    path("reject_all/", views.consent_reject_all, name="reject_all_alias"),

    # ------------------------------------------------------------------
    # Legacy alias (deprecated, kept for JS compatibility)
    # ------------------------------------------------------------------
    path("save/", views.consent_accept, name="save"),

    # ------------------------------------------------------------------
    # JSON API (canonical, frontend-safe)
    # ------------------------------------------------------------------
    path(
        "api/status/",
        lazy_view("apps.consent.api.get_consent_status"),
        name="api_status",
    ),
    path(
        "api/update/",
        lazy_view("apps.consent.api.update_consent"),
        name="api_update",
    ),
]
