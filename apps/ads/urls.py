from django.urls import path
from . import views

app_name = "ads"

urlpatterns = [
    path("api/placements/", views.list_placements, name="list_placements"),
    path("api/events/", views.record_event, name="record_event"),
    path("api/fill/", views.fill_ad, name="fill_ad"),
    path("api/click/", views.record_click, name="record_click"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/toggles/", views.toggle_settings, name="toggle_settings"),
]
