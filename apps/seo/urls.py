from django.urls import path
from . import views

app_name = "seo"

urlpatterns = [
    path("api/metadata/", views.metadata_view, name="metadata"),
    path("api/metadata/regenerate/", views.regenerate_metadata, name="regenerate_metadata"),
    path("api/metadata/controls/", views.update_metadata_controls, name="update_metadata_controls"),
    path("api/links/apply/", views.apply_link_suggestion, name="apply_link_suggestion"),
    path("api/inspect/", views.inspect_url_view, name="inspect_url"),
    path("redirects/manage/", views.manage_redirect, name="manage_redirect"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
