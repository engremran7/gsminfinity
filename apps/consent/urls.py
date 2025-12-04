
from django.urls import path

from . import views

app_name = "consent"

urlpatterns = [
    path("privacy/", views.privacy_center, name="privacy_center"),
    path("banner/", views.banner, name="banner"),
    path("accept_all/", views.accept_all, name="accept_all"),
    path("reject_all/", views.reject_all, name="reject_all"),
    path("accept/", views.accept, name="accept"),
]


