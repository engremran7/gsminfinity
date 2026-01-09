"""
Public API surface for the i18n + Themes micro-app, loaded dynamically via AppService.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.http import HttpRequest

from apps.i18n.services import (
    get_bundle,
    register_manifest,
    resolve_key,
    resolve_locale,
    resolve_theme,
)


def bundle(
    app_id: str,
    locale: str,
    namespaces: Iterable[str] | None = None,
    since_version: int | None = None,
) -> dict[str, Any]:
    return get_bundle(app_id, locale, namespaces, since_version)


def t(
    app_id: str, key: str, locale: str, default: str = "", site_id: str | None = None
) -> str:
    return resolve_key(app_id, locale, key, default=default, site_id=site_id)


def locale_for_request(
    request: HttpRequest, app_id: str, site_id: str | None = None
) -> str:
    return resolve_locale(request, app_id, site_id)


def theme_for_request(
    request: HttpRequest,
    app_id: str,
    site_id: str | None = None,
    route: str | None = None,
) -> dict[str, Any]:
    user_id = (
        str(getattr(getattr(request, "user", None), "pk", ""))
        if getattr(request, "user", None)
        else None
    )
    device_pref = request.COOKIES.get("theme_pref")
    system_pref = request.META.get("HTTP_SEC_CH_PREFERS_COLOR_SCHEME")
    return resolve_theme(
        app_id,
        locale_for_request(request, app_id, site_id),
        site_id,
        route,
        user_id,
        device_pref,
        system_pref,
    )


__all__ = [
    "bundle",
    "t",
    "locale_for_request",
    "theme_for_request",
    "register_manifest",
]
