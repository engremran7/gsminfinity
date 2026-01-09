from django.urls import path

from . import services_view, views

app_name = "ai"

urlpatterns = [
    path("", views.models_view, name="models"),
    path("execute/", views.execute_view, name="execute"),
    path("settings/", views.settings_view, name="settings"),
    path("ops/", services_view.ops_dashboard, name="ops"),
]
