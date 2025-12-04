
from __future__ import annotations

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils import translation

from apps.i18n_themes.api import locale_for_request


@require_POST
def switch_locale(request):
    target = request.POST.get("locale") or request.GET.get("locale")
    fallback = locale_for_request(request, app_id="core")
    locale = target or fallback
    # Activate immediately for this response/session
    translation.activate(locale)

    resp = HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("core:home")))
    resp.set_cookie("lang", locale, max_age=60 * 60 * 24 * 365, samesite="Lax")
    resp.set_cookie("django_language", locale, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


