from django.urls import path

from . import views

app_name = "security_suite"

urlpatterns = [
    path("status/", views.security_status, name="security_status"),
]
