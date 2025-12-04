
from django.urls import path

from apps.ai import views

app_name = "ai"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
    path("models/", views.models_view, name="models"),
    path("execute/", views.execute_view, name="execute"),
]


