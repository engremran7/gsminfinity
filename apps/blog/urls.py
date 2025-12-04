
from django.urls import path

from . import views
from . import feeds

app_name = "blog"

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("create/", views.post_create, name="post_create"),
    path("feed/rss/", feeds.LatestRssFeed(), name="feed_rss"),
    path("feed/atom/", feeds.LatestAtomFeed(), name="feed_atom"),
    path("feed/json/", feeds.json_feed, name="feed_json"),
    path("api/ai/assist/", views.api_ai_assist, name="api_ai_assist"),
    path("api/similar/", views.api_similar_posts, name="api_similar_posts"),
    path("api/workflow/<slug:slug>/", views.api_workflow, name="api_workflow"),
    path("api/posts/", views.api_posts, name="api_posts"),
    path("api/posts/<slug:slug>/related/", views.api_related, name="api_related"),
    path("api/autosave/", views.post_autosave, name="post_autosave"),
    path("api/preview/", views.post_preview, name="post_preview"),
    path("api/widgets/trending-tags/", views.widget_trending_tags, name="widget_trending_tags"),
    path("api/widgets/latest/", views.widget_latest_posts, name="widget_latest_posts"),
    path("api/widgets/top/", views.widget_top_posts, name="widget_top_posts"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
]


