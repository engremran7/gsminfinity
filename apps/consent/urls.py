from __future__ import annotations

from django.urls import path
from . import views
from apps.consent.api import get_consent_status, update_consent

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
    # Compatibility aliases for underscore URLs
    # Required because your frontend still calls:
    #   /consent/accept_all/
    #   /consent/reject_all/
    # DO NOT REMOVE
    # ------------------------------------------------------------------
    path("accept_all/", views.consent_accept_all, name="accept_all_u"),
    path("reject_all/", views.consent_reject_all, name="reject_all_u"),

    # ------------------------------------------------------------------
    # Legacy alias: confirmed in frontend JS
    # ------------------------------------------------------------------
    path("save/", views.consent_accept, name="save"),

    # ------------------------------------------------------------------
    # JSON API (Clean, canonical, frontend-safe)
    # apps/consent/api.py
    # ------------------------------------------------------------------
    path("api/status/", get_consent_status, name="api_status"),
    path("api/update/", update_consent, name="api_update"),
]
