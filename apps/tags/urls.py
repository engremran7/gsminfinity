from django.urls import path

from . import views

app_name = "tags"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("suggest/", views.suggest_tags, name="suggest"),
    path("merge/", views.merge_tags, name="merge"),
    path("analytics/", views.tag_analytics, name="analytics"),
    path("", views.tag_list, name="list"),
    path("<slug:slug>/", views.tag_detail, name="detail"),
]
