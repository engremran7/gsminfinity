"""
apps.consent.urls
-----------------
URL configuration for user consent management and GDPR compliance system.

✅ Provides:
    - Accept / manage consent preferences
    - Render consent banner partial (for inclusion in templates)
    - API-like endpoint for SPA polling or JS SDKs (`/status/`)
    - Backward-compatible aliases for older template calls

This module is part of the GSMInfinity Enterprise Consent Suite.
"""

from django.urls import path
from .views import (
    consent_accept,
    manage_consent,
    banner_partial,
    consent_status,   # ✅ added for SPA / monitoring usage
)

urlpatterns = [
    # ============================================================
    #  Core Consent Endpoints
    # ============================================================
    path("accept/", consent_accept, name="consent_accept"),
    path("manage/", manage_consent, name="consent_manage"),
    path("banner/", banner_partial, name="consent_banner"),

    # ============================================================
    #  API / Utility Endpoints
    # ============================================================
    path("status/", consent_status, name="consent_status"),  # ✅ NEW
    path("accept-all/", consent_accept, name="consent_accept_all"),
    path("save/", consent_accept, name="consent_save"),  # alias for legacy frontend
]

# Optional tip:
# If you plan to expose a JSON endpoint for SPA apps or SDK clients,
# the `consent_status` view should return a JSONResponse like:
#
#   {
#       "has_consent": True,
#       "required_categories": [...],
#       "user_choices": {...}
#   }
#
# That endpoint is lightweight and ideal for consent audit logging or banner state.
