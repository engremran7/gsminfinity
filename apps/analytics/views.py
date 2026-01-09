"""
Analytics Views
Real-time analytics dashboard and API endpoints
"""

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import DailyMetrics, Event, PageView, RealtimeMetrics, UserAnalytics


@staff_member_required
def analytics_dashboard(request):
    """
    Main analytics dashboard for staff users.
    Shows comprehensive metrics and charts.
    """
    # Get today's metrics
    today = timezone.now().date()
    today_metrics = DailyMetrics.objects.filter(date=today).first()

    # Get last 30 days metrics
    thirty_days_ago = today - timedelta(days=30)
    last_30_days = DailyMetrics.objects.filter(date__gte=thirty_days_ago).order_by(
        "-date"
    )

    # Calculate totals
    total_page_views = sum(m.total_page_views for m in last_30_days)
    total_downloads = sum(m.total_downloads for m in last_30_days)
    total_searches = sum(m.total_searches for m in last_30_days)

    context = {
        "today_metrics": today_metrics,
        "last_30_days": last_30_days,
        "total_page_views": total_page_views,
        "total_downloads": total_downloads,
        "total_searches": total_searches,
    }

    return render(request, "analytics/dashboard.html", context)


@staff_member_required
def realtime_dashboard(request):
    """
    Real-time analytics dashboard with live updates.
    """
    # Get latest realtime metrics
    latest_metrics = RealtimeMetrics.objects.order_by("-timestamp").first()

    context = {
        "metrics": latest_metrics,
    }

    return render(request, "analytics/realtime_dashboard.html", context)


@require_http_methods(["POST"])
def track_pageview(request):
    """
    Track a page view.
    Called via AJAX from frontend.
    """
    try:
        PageView.objects.create(
            path=request.POST.get("path", request.path),
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR"),
            referrer=request.META.get("HTTP_REFERER", ""),
            session_key=request.session.session_key,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@require_http_methods(["POST"])
def track_event(request):
    """
    Track a custom event.
    Called via AJAX from frontend.
    """
    try:
        Event.objects.create(
            event_type=request.POST.get("event_type", "custom"),
            event_name=request.POST.get("event_name", ""),
            event_data=request.POST.get("event_data", {}),
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR"),
            session_key=request.session.session_key,
        )
        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def daily_metrics(request):
    """
    Get daily metrics for a date range.
    """
    days = int(request.GET.get("days", 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    metrics = DailyMetrics.objects.filter(
        date__gte=start_date, date__lte=end_date
    ).order_by("date")

    data = [
        {
            "date": m.date.isoformat(),
            "page_views": m.total_page_views,
            "unique_visitors": m.unique_visitors,
            "downloads": m.total_downloads,
            "searches": m.total_searches,
        }
        for m in metrics
    ]

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def realtime_metrics(request):
    """
    Get current real-time metrics.
    """
    latest = RealtimeMetrics.objects.order_by("-timestamp").first()

    if not latest:
        return Response(
            {
                "active_users": 0,
                "page_views_last_hour": 0,
                "downloads_last_hour": 0,
            }
        )

    return Response(
        {
            "timestamp": latest.timestamp.isoformat(),
            "active_users": latest.active_users,
            "page_views_last_hour": latest.page_views_last_hour,
            "downloads_last_hour": latest.downloads_last_hour,
            "top_pages": latest.top_pages_now,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_analytics(request):
    """
    Get analytics for the current user.
    """
    analytics, created = UserAnalytics.objects.get_or_create(user=request.user)

    return Response(
        {
            "total_page_views": analytics.total_page_views,
            "total_downloads": analytics.total_downloads,
            "total_uploads": analytics.total_uploads,
            "total_comments": analytics.total_comments,
            "days_active": analytics.days_active,
            "favorite_brands": analytics.favorite_brands,
            "favorite_categories": analytics.favorite_categories,
        }
    )


@staff_member_required
def traffic_report(request):
    """Traffic analysis report"""
    return render(request, "analytics/reports/traffic.html")


@staff_member_required
def engagement_report(request):
    """User engagement report"""
    return render(request, "analytics/reports/engagement.html")


@staff_member_required
def content_report(request):
    """Content performance report"""
    return render(request, "analytics/reports/content.html")
