"""
Enhanced URL routing for Comment API endpoints.
"""
from django.urls import path
from apps.comments import api_enhanced

app_name = "comments_api"

urlpatterns = [
    # List and create
    path("", api_enhanced.list_comments_api, name="list"),
    path("create/", api_enhanced.create_comment_api, name="create"),
    
    # Individual comment actions
    path("<int:comment_id>/react/", api_enhanced.react_to_comment_api, name="react"),
    path("<int:comment_id>/vote/", api_enhanced.vote_comment_api, name="vote"),
    path("<int:comment_id>/flag/", api_enhanced.flag_comment_api, name="flag"),
    path("<int:comment_id>/bookmark/", api_enhanced.bookmark_comment_api, name="bookmark"),
    path("<int:comment_id>/moderate/", api_enhanced.moderate_comment_api, name="moderate"),
    
    # Threading and analytics
    path("<int:comment_id>/thread/", api_enhanced.get_comment_thread_api, name="thread"),
    path("top/", api_enhanced.get_top_comments_api, name="top"),
]
