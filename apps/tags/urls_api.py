"""
Enhanced URL routing for Tag API endpoints.
"""
from django.urls import path
from apps.tags import api_enhanced

app_name = "tags_api"

urlpatterns = [
    # Search and list
    path("search/", api_enhanced.search_tags_api, name="search"),
    path("", api_enhanced.list_tags_api, name="list"),
    path("trending/", api_enhanced.get_trending_tags_api, name="trending"),
    path("categories/", api_enhanced.get_tag_categories_api, name="categories"),
    
    # Tag details and relationships
    path("<slug:slug>/", api_enhanced.get_tag_api, name="detail"),
    path("<slug:slug>/related/", api_enhanced.get_related_tags_api, name="related"),
    
    # Subscriptions
    path("<slug:slug>/subscribe/", api_enhanced.subscribe_to_tag_api, name="subscribe"),
    path("<slug:slug>/unsubscribe/", api_enhanced.unsubscribe_from_tag_api, name="unsubscribe"),
    
    # Suggestions and AI
    path("suggest/content/", api_enhanced.suggest_tags_for_content_api, name="suggest_content"),
    path("suggest/create/", api_enhanced.create_tag_suggestion_api, name="create_suggestion"),
    path("suggest/<int:suggestion_id>/approve/", api_enhanced.approve_tag_suggestion_api, name="approve_suggestion"),
    
    # Staff actions
    path("merge/", api_enhanced.merge_tags_api, name="merge"),
    
    # User collections
    path("collections/my-subscriptions/", api_enhanced.get_user_tag_subscriptions_api, name="my_subscriptions"),
    path("collections/create/", api_enhanced.create_tag_collection_api, name="create_collection"),
]
