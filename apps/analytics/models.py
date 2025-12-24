"""
Analytics Models
Real-time metrics and historical analytics
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class PageView(models.Model):
    """Track page views for analytics"""
    path = models.CharField(max_length=500, db_index=True)  # Standalone index for path-only queries
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_views'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'analytics_pageview'
        indexes = [
            models.Index(fields=['path', '-created_at'], name='pageview_path_idx'),
            models.Index(fields=['user', '-created_at'], name='pageview_user_idx'),
            models.Index(fields=['-created_at'], name='pageview_created_idx'),
        ]
        ordering = ['-created_at']


class Event(models.Model):
    """Track custom events for analytics"""
    EVENT_TYPES = [
        ('download', 'Download'),
        ('search', 'Search'),
        ('share', 'Share'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('signup', 'Signup'),
        ('login', 'Login'),
        ('upload', 'Upload'),
        ('custom', 'Custom'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    event_name = models.CharField(max_length=200)
    event_data = models.JSONField(default=dict, blank=True)
    
    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    user = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events'
    )
    session_key = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'analytics_event'
        indexes = [
            models.Index(fields=['event_type', '-created_at'], name='event_type_idx'),
            models.Index(fields=['user', '-created_at'], name='event_user_idx'),
            models.Index(fields=['content_type', 'object_id'], name='event_content_idx'),
        ]
        ordering = ['-created_at']


class DailyMetrics(models.Model):
    """Aggregated daily metrics"""
    date = models.DateField(unique=True, db_index=True)
    
    # Traffic metrics
    total_page_views = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    
    # Engagement metrics
    total_downloads = models.PositiveIntegerField(default=0)
    total_searches = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_likes = models.PositiveIntegerField(default=0)
    
    # Content metrics
    new_blog_posts = models.PositiveIntegerField(default=0)
    new_firmwares = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    avg_page_load_time = models.FloatField(default=0.0)
    avg_api_response_time = models.FloatField(default=0.0)
    
    # Additional data
    top_pages = models.JSONField(default=list, blank=True)
    top_searches = models.JSONField(default=list, blank=True)
    top_downloads = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_daily_metrics'
        ordering = ['-date']
        verbose_name_plural = 'Daily Metrics'


class RealtimeMetrics(models.Model):
    """Real-time metrics snapshot (updated every minute)"""
    timestamp = models.DateTimeField(unique=True, db_index=True)
    
    # Current active users (last 5 minutes)
    active_users = models.PositiveIntegerField(default=0)
    
    # Current hour metrics
    page_views_last_hour = models.PositiveIntegerField(default=0)
    downloads_last_hour = models.PositiveIntegerField(default=0)
    searches_last_hour = models.PositiveIntegerField(default=0)
    
    # System metrics
    cpu_usage = models.FloatField(default=0.0)
    memory_usage = models.FloatField(default=0.0)
    disk_usage = models.FloatField(default=0.0)
    
    # Additional data
    top_pages_now = models.JSONField(default=list, blank=True)
    active_downloads = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'analytics_realtime_metrics'
        ordering = ['-timestamp']
        verbose_name_plural = 'Realtime Metrics'


class UserAnalytics(models.Model):
    """Per-user analytics summary"""
    user = models.OneToOneField(
        'users.CustomUser',
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    
    # Lifetime metrics
    total_page_views = models.PositiveIntegerField(default=0)
    total_downloads = models.PositiveIntegerField(default=0)
    total_uploads = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_likes_given = models.PositiveIntegerField(default=0)
    total_likes_received = models.PositiveIntegerField(default=0)
    
    # Engagement metrics
    last_active_at = models.DateTimeField(null=True, blank=True)
    days_active = models.PositiveIntegerField(default=0)
    avg_session_duration = models.FloatField(default=0.0)  # minutes
    
    # Preferences (learned from behavior)
    favorite_brands = models.JSONField(default=list, blank=True)
    favorite_categories = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'analytics_user_analytics'
        verbose_name_plural = 'User Analytics'

