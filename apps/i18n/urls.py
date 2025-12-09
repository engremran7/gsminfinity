
from django.urls import path

from apps.i18n import views, views_switcher

app_name = "i18n"

urlpatterns = [
    path("bundle/", views.bundle_view, name="bundle"),
    path("theme/", views.theme_view, name="theme"),
    path("manifest/", views.manifest_view, name="manifest"),
    path("switch/", views_switcher.switch_locale, name="switch"),
    path("api/translate/", views.translate_texts, name="translate_texts"),
]


