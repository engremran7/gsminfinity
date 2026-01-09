"""
Legacy core URL aliases. All public pages are served by apps.pages.
These redirects are kept for compatibility with older templates.
"""

from django.urls import path
from django.views.generic import RedirectView

app_name = "core"

urlpatterns = [
    path(
        "privacy/",
        RedirectView.as_view(url="/privacy/", permanent=True),
        name="privacy",
    ),
    path("terms/", RedirectView.as_view(url="/terms/", permanent=True), name="terms"),
    path(
        "cookies/",
        RedirectView.as_view(url="/cookies/", permanent=True),
        name="cookies",
    ),
]
