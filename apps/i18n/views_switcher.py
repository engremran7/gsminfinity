
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.i18n.api import locale_for_request
from apps.i18n.models import Locale


@require_POST
def switch_locale(request):
    target = request.POST.get("locale") or request.GET.get("locale")
    fallback = locale_for_request(request, app_id="core")
    locale = target or fallback
    # Validate against known locales to avoid arbitrary inputs
    allowed_codes = set(Locale.objects.values_list("code", flat=True))
    if locale not in allowed_codes:
        locale = fallback

    # Activate immediately for this response/session
    translation.activate(locale)

    try:
        fallback_url = reverse("home")
    except Exception:
        fallback_url = "/"

    # Security: Validate referer to prevent open redirect attacks
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts=settings.ALLOWED_HOSTS):
        redirect_url = referer
    else:
        redirect_url = fallback_url

    resp = HttpResponseRedirect(redirect_url)
    cookie_opts = {"max_age": 60 * 60 * 24 * 365, "samesite": "Lax", "secure": not settings.DEBUG}
    resp.set_cookie("lang", locale, **cookie_opts)
    resp.set_cookie("django_language", locale, **cookie_opts)
    return resp
