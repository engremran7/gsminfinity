from django.urls import path

from . import views

app_name = "devices"

urlpatterns = [
    path("my/", views.my_devices, name="my_devices"),
    path("events/", views.device_events, name="device_events"),
    path("payload/", views.device_payload_view, name="device_payload"),
]
