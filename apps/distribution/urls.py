from django.urls import path

from . import api, views

app_name = "distribution"

urlpatterns = [
    path("api/test/<slug:slug>/", api.api_send_test, name="api_send_test"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
