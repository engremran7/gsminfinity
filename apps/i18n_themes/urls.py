
from django.urls import path

from apps.i18n_themes import views, views_switcher

app_name = "i18n_themes"

urlpatterns = [
    path("bundle/", views.bundle_view, name="bundle"),
    path("theme/", views.theme_view, name="theme"),
    path("manifest/", views.manifest_view, name="manifest"),
    path("switch/", views_switcher.switch_locale, name="switch"),
]


