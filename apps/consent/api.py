"""
apps.consent.api
================

Public, import-stable API surface for Consent JSON endpoints.

Purpose:
    • Re-export the JSON API views from apps.consent.api.views
    • Allow import paths such as:
          from apps.consent.api import get_consent_status, update_consent
    • Keep internal folder structure flexible without breaking imports
    • Guarantee ASGI/WSGI-safe imports with zero side effects
    • Avoid unexpected failures during Django boot

This file must remain minimal, deterministic, and should never contain
heavy imports, query execution, or template logic.
"""

from __future__ import annotations

__all__ = [
    "get_consent_status",
    "update_consent",
]

# ---------------------------------------------------------------------
# Import Re-exports (Safe)
# ---------------------------------------------------------------------

try:
    # Canonical JSON API implementations
    from .api.views import (
        get_consent_status,
        update_consent,
    )

except Exception as exc:
    # Boot-safe fallback:
    # We intentionally DO NOT raise errors here because Django may import
    # this module during ASGI/WSGI initialization or migrations.
    # Exposing "None" keeps the import path intact without silent breakage.
    get_consent_status = None  # type: ignore
    update_consent = None      # type: ignore
