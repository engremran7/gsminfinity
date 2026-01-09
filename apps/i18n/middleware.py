from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin

from apps.i18n.api import locale_for_request


class LocaleMiddleware(MiddlewareMixin):
    """
    Attach resolved locale + direction to request using the i18n resolver.
    """

    def process_request(self, request):
        locale = locale_for_request(request, app_id="core", site_id=None)
        request.locale = locale
        request.direction = (
            "rtl" if locale.startswith(("ar", "ur", "fa", "ps")) else "ltr"
        )
