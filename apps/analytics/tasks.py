"""
Analytics Celery Tasks
Automated aggregation and real-time updates
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def aggregate_daily_metrics(self, date=None):
    """
    Aggregate daily metrics for a specific date.
    Runs daily at midnight to aggregate previous day's data.
    """
    try:
        from apps.analytics.models import PageView, Event, DailyMetrics
        from apps.blog.models import Post
        from apps.firmwares.models import OfficialFirmware
        
        if date is None:
            # Default to yesterday
            date = (timezone.now() - timedelta(days=1)).date()
        
        logger.info(f"Aggregating daily metrics for {date}")
        
        # Count page views
        total_page_views = PageView.objects.filter(
            created_at__date=date
        ).count()
        
        # Count unique visitors (by session)
        unique_visitors = PageView.objects.filter(
            created_at__date=date
        ).values('session_key').distinct().count()
        
        # Count new users
        from apps.users.models import CustomUser
        new_users = CustomUser.objects.filter(
            date_joined__date=date
        ).count()
        
        # Count events by type
        total_downloads = Event.objects.filter(
            created_at__date=date,
            event_type='download'
        ).count()
        
        total_searches = Event.objects.filter(
            created_at__date=date,
            event_type='search'
        ).count()
        
        total_comments = Event.objects.filter(
            created_at__date=date,
            event_type='comment'
        ).count()
        
        total_likes = Event.objects.filter(
            created_at__date=date,
            event_type='like'
        ).count()
        
        # Count new content
        new_blog_posts = Post.objects.filter(
            created_at__date=date
        ).count()
        
        new_firmwares = OfficialFirmware.objects.filter(
            created_at__date=date
        ).count()
        
        # Get top pages
        top_pages = list(
            PageView.objects.filter(created_at__date=date)
            .values('path')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        # Get top searches
        top_searches = list(
            Event.objects.filter(
                created_at__date=date,
                event_type='search'
            )
            .values('event_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        # Create or update daily metrics
        metrics, created = DailyMetrics.objects.update_or_create(
            date=date,
            defaults={
                'total_page_views': total_page_views,
                'unique_visitors': unique_visitors,
                'new_users': new_users,
                'total_downloads': total_downloads,
                'total_searches': total_searches,
                'total_comments': total_comments,
                'total_likes': total_likes,
                'new_blog_posts': new_blog_posts,
                'new_firmwares': new_firmwares,
                'top_pages': top_pages,
                'top_searches': top_searches,
            }
        )
        
        logger.info(f"Daily metrics aggregated: {total_page_views} page views, {unique_visitors} unique visitors")
        
        return {
            'status': 'success',
            'date': str(date),
            'page_views': total_page_views,
            'unique_visitors': unique_visitors
        }
        
    except Exception as exc:
        logger.error(f"Daily metrics aggregation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task
def update_realtime_metrics():
    """
    Update real-time metrics snapshot.
    Runs every minute to provide live dashboard data.
    """
    try:
        from apps.analytics.models import PageView, Event, RealtimeMetrics
        import psutil
        
        now = timezone.now()
        five_min_ago = now - timedelta(minutes=5)
        one_hour_ago = now - timedelta(hours=1)
        
        # Active users (last 5 minutes)
        active_users = PageView.objects.filter(
            created_at__gte=five_min_ago
        ).values('session_key').distinct().count()
        
        # Last hour metrics
        page_views_last_hour = PageView.objects.filter(
            created_at__gte=one_hour_ago
        ).count()
        
        downloads_last_hour = Event.objects.filter(
            created_at__gte=one_hour_ago,
            event_type='download'
        ).count()
        
        searches_last_hour = Event.objects.filter(
            created_at__gte=one_hour_ago,
            event_type='search'
        ).count()
        
        # Top pages right now
        top_pages_now = list(
            PageView.objects.filter(created_at__gte=five_min_ago)
            .values('path')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Create snapshot
        RealtimeMetrics.objects.create(
            timestamp=now,
            active_users=active_users,
            page_views_last_hour=page_views_last_hour,
            downloads_last_hour=downloads_last_hour,
            searches_last_hour=searches_last_hour,
            cpu_usage=cpu_usage,
            memory_usage=memory.percent,
            disk_usage=disk.percent,
            top_pages_now=top_pages_now,
        )
        
        # Cleanup old snapshots (keep last 24 hours)
        cutoff = now - timedelta(hours=24)
        RealtimeMetrics.objects.filter(timestamp__lt=cutoff).delete()
        
        logger.debug(f"Realtime metrics updated: {active_users} active users")
        
        return {
            'status': 'success',
            'active_users': active_users,
            'timestamp': now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Realtime metrics update failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }

