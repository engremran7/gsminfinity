"""
Analytics App URLs
Real-time analytics dashboard and API endpoints
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "analytics"

router = DefaultRouter()
# ViewSets will be registered here when created

urlpatterns = [
    # Dashboard
    path("dashboard/", views.analytics_dashboard, name="dashboard"),
    path("dashboard/realtime/", views.realtime_dashboard, name="realtime_dashboard"),
    # API Endpoints
    path("api/track/pageview/", views.track_pageview, name="track_pageview"),
    path("api/track/event/", views.track_event, name="track_event"),
    path("api/metrics/daily/", views.daily_metrics, name="daily_metrics"),
    path("api/metrics/realtime/", views.realtime_metrics, name="realtime_metrics"),
    path("api/user/analytics/", views.user_analytics, name="user_analytics"),
    # Reports
    path("reports/traffic/", views.traffic_report, name="traffic_report"),
    path("reports/engagement/", views.engagement_report, name="engagement_report"),
    path("reports/content/", views.content_report, name="content_report"),
    # ViewSet routes
    path("", include(router.urls)),
]
