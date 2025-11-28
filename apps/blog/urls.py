from django.urls import path

from . import views

app_name = "blog"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("create/", views.post_create, name="post_create"),
    path("api/posts/", views.api_posts, name="api_posts"),
    path("api/posts/<slug:slug>/related/", views.api_related, name="api_related"),
    path("api/autosave/", views.post_autosave, name="post_autosave"),
    path("api/preview/", views.post_preview, name="post_preview"),
    path("api/widgets/trending-tags/", views.widget_trending_tags, name="widget_trending_tags"),
    path("api/widgets/latest/", views.widget_latest_posts, name="widget_latest_posts"),
    path("api/widgets/top/", views.widget_top_posts, name="widget_top_posts"),
    path("api/widgets/bounty/", views.widget_bounty_posts, name="widget_bounty_posts"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
]
