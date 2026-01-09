from django.urls import path

from apps.app_registry import views

app_name = "app_registry"

urlpatterns = [
    path("", views.registry_list, name="registry_list"),
    path("<str:app_id>/", views.registry_detail, name="registry_detail"),
]
