# Home Page Widget Service - Modular, Signal-Based Architecture
"""
Provides data for homepage widgets including:
- Latest firmwares (all types)
- Trending firmwares (based on views/downloads)
- Latest blog posts
- Trending blog posts
- Most requested firmwares
- Auto ad placement logic

Uses signals for loose coupling with other apps
"""

from django.apps import apps
from django.utils import timezone
from django.db.models import Count, Q, F, Sum
from django.core.cache import cache
from datetime import timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class HomePageWidgetService:
    """Central service for all homepage widget data - optimized with caching"""
    
    CACHE_TIMEOUT = 300  # 5 minutes cache for high-traffic homepage
    
    # === FIRMWARE WIDGETS ===
    
    @classmethod
    def get_latest_firmwares(cls, limit: int = 10) -> List:
        """
        Get latest approved firmwares across all types
        
        Returns list of dicts with: id, type, brand, model, variant, uploaded_at, download_count
        """
        cache_key = f'homepage_latest_firmwares_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        
        # Check if firmwares app is installed (modularity check)
        if not apps.is_installed('apps.firmwares'):
            return results
        
        # Get all firmware types (Official, Engineering, etc.)
        firmware_types = [
            ('OfficialFirmware', 'Official'),
            ('EngineeringFirmware', 'Engineering'),
            ('ReadbackFirmware', 'Readback'),
            ('ModifiedFirmware', 'Modified'),
            ('OtherFirmware', 'Other'),
        ]
        
        all_firmwares = []
        
        for model_name, display_name in firmware_types:
            try:
                Model = apps.get_model('firmwares', model_name)
                firmwares = Model.objects.select_related(
                    'brand', 'model', 'variant'
                ).order_by('-created_at')[:limit]
                
                for fw in firmwares:
                    all_firmwares.append({
                        'id': str(fw.id),
                        'type': display_name,
                        'type_slug': model_name.lower(),
                        'brand': fw.brand.name if fw.brand else 'Unknown',
                        'brand_slug': fw.brand.slug if fw.brand else 'unknown',
                        'model': fw.model.name if fw.model else 'Unknown',
                        'model_slug': fw.model.slug if fw.model else 'unknown',
                        'variant': fw.variant.name if fw.variant else 'Unknown',
                        'variant_slug': fw.variant.slug if fw.variant else 'unknown',
                        'uploaded_at': fw.created_at,
                        'file_name': fw.original_file_name,
                        'chipset': fw.chipset or 'N/A',
                        'has_password': fw.is_password_protected,
                    })
            except Exception as e:
                logger.warning(f"Error fetching {model_name}: {e}")
                continue
        
        # Sort by date and limit
        all_firmwares.sort(key=lambda x: x['uploaded_at'], reverse=True)
        results = all_firmwares[:limit]
        
        cache.set(cache_key, results, cls.CACHE_TIMEOUT)
        return results
    
    @classmethod
    def get_trending_firmwares(cls, limit: int = 10, days: int = 7) -> List:
        """
        Get trending firmwares based on views/downloads in last N days
        
        Uses FirmwareStats for efficient queries
        """
        cache_key = f'homepage_trending_firmwares_{limit}_{days}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        
        if not apps.is_installed('apps.firmwares'):
            return results
        
        try:
            FirmwareStats = apps.get_model('firmwares', 'FirmwareStats')
            
            # Get stats from last N days, aggregate by firmware
            start_date = timezone.now().date() - timedelta(days=days)
            
            trending = FirmwareStats.objects.filter(
                date__gte=start_date
            ).values(
                'content_type', 'object_id'
            ).annotate(
                total_views=Sum('view_count'),
                total_downloads=Sum('successful_downloads'),
                # Trending score: views * 0.3 + downloads * 0.7
                score=Sum(F('view_count') * 0.3 + F('successful_downloads') * 0.7)
            ).order_by('-score')[:limit]
            
            # Fetch actual firmware objects
            from django.contrib.contenttypes.models import ContentType
            
            for stat in trending:
                try:
                    ct = ContentType.objects.get(id=stat['content_type'])
                    firmware = ct.get_object_for_this_type(id=stat['object_id'])
                    
                    results.append({
                        'id': str(firmware.id),
                        'type': ct.model.replace('firmware', '').title(),
                        'type_slug': ct.model,
                        'brand': firmware.brand.name if firmware.brand else 'Unknown',
                        'brand_slug': firmware.brand.slug if firmware.brand else 'unknown',
                        'model': firmware.model.name if firmware.model else 'Unknown',
                        'model_slug': firmware.model.slug if firmware.model else 'unknown',
                        'variant': firmware.variant.name if firmware.variant else 'Unknown',
                        'variant_slug': firmware.variant.slug if firmware.variant else 'unknown',
                        'views': stat['total_views'],
                        'downloads': stat['total_downloads'],
                        'trending_score': round(stat['score'], 2),
                        'file_name': firmware.original_file_name,
                    })
                except Exception as e:
                    logger.warning(f"Error fetching firmware for trending: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error getting trending firmwares: {e}")
        
        cache.set(cache_key, results, cls.CACHE_TIMEOUT)
        return results
    
    @classmethod
    def get_most_requested_firmwares(cls, limit: int = 10) -> List:
        """Get most requested firmwares from FirmwareRequest model"""
        cache_key = f'homepage_most_requested_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        
        if not apps.is_installed('apps.firmwares'):
            return results
        
        try:
            FirmwareRequest = apps.get_model('firmwares', 'FirmwareRequest')
            
            requests = FirmwareRequest.objects.filter(
                status='open'
            ).select_related('brand', 'model').order_by('-request_count')[:limit]
            
            for req in requests:
                results.append({
                    'id': req.id,
                    'brand': req.brand.name,
                    'brand_slug': req.brand.slug,
                    'model': req.model.name if req.model else 'Various Models',
                    'model_slug': req.model.slug if req.model else 'various',
                    'variant': req.variant_name or 'Not specified',
                    'firmware_type': req.firmware_type,
                    'request_count': req.request_count,
                    'urgency': req.get_urgency_display(),
                    'last_requested': req.last_requested_at,
                    'description_preview': req.description[:100] if req.description else '',
                })
        except Exception as e:
            logger.error(f"Error getting most requested: {e}")
        
        cache.set(cache_key, results, cls.CACHE_TIMEOUT)
        return results
    
    # === BLOG WIDGETS ===
    
    @classmethod
    def get_latest_blogs(cls, limit: int = 10) -> List:
        """Get latest published blog posts"""
        cache_key = f'homepage_latest_blogs_{limit}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        
        if not apps.is_installed('apps.blog'):
            return results
        
        try:
            Post = apps.get_model('blog', 'Post')
            
            posts = Post.objects.filter(
                is_published=True,
                published_at__isnull=False
            ).select_related('author').order_by('-published_at')[:limit]
            
            for post in posts:
                results.append({
                    'id': post.id,
                    'title': post.title,
                    'slug': post.slug,
                    'excerpt': post.summary or post.body[:200],
                    'author': post.author.get_full_name() if post.author else 'Staff',
                    'published_at': post.published_at,
                    'view_count': getattr(post, 'view_count', 0),
                    'comment_count': 0,
                    'featured_image': post.hero_image,
                })
        except Exception as e:
            logger.error(f"Error getting latest blogs: {e}")
        
        cache.set(cache_key, results, cls.CACHE_TIMEOUT)
        return results
    
    @classmethod
    def get_trending_blogs(cls, limit: int = 10, days: int = 7) -> List:
        """Get trending blog posts based on views in last N days"""
        cache_key = f'homepage_trending_blogs_{limit}_{days}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        
        if not apps.is_installed('apps.blog'):
            return results
        
        try:
            Post = apps.get_model('blog', 'Post')
            
            # Check if blog has analytics
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Simple trending based on recent posts only (no views tracking yet)
            posts = Post.objects.filter(
                is_published=True,
                published_at__gte=cutoff_date
            ).select_related('author').order_by('-published_at')[:limit]
            
            for post in posts:
                results.append({
                    'id': post.id,
                    'title': post.title,
                    'slug': post.slug,
                    'excerpt': post.summary or post.body[:200],
                    'author': post.author.get_full_name() if post.author else 'Staff',
                    'published_at': post.published_at,
                    'view_count': 0,  # To be implemented
                    'trending_score': 1,  # To be implemented
                })
        except Exception as e:
            logger.error(f"Error getting trending blogs: {e}")
        
        cache.set(cache_key, results, cls.CACHE_TIMEOUT)
        return results
    
    # === AD PLACEMENT LOGIC ===
    
    @classmethod
    def get_ad_placements(cls, page_layout: str = 'dual_column') -> Dict:
        """
        Calculate optimal ad placements based on content length and layout
        
        Args:
            page_layout: 'dual_column', 'single_column', 'grid', etc.
        
        Returns:
            Dict with ad slot positions and configs
        """
        if not apps.is_installed('apps.ads'):
            return {'slots': []}
        
        try:
            AdPlacement = apps.get_model('ads', 'AdPlacement')
            
            # Get active placements for homepage
            # The Ad model uses 'context' field, not 'page_type'
            placements = AdPlacement.objects.filter(
                context='homepage',
                is_active=True
            ).order_by('slug')  # Order by slug since there's no priority field
            
            slots = []
            
            if page_layout == 'dual_column':
                # Dual column: ads between widgets
                slots = [
                    {
                        'position': 'top_banner',
                        'size': '728x90',  # Leaderboard
                        'after_widget': None,  # Before all widgets
                        'column': 'full',
                    },
                    {
                        'position': 'left_sidebar_1',
                        'size': '300x250',  # Medium rectangle
                        'after_widget': 2,  # After 2nd widget in left column
                        'column': 'left',
                    },
                    {
                        'position': 'right_sidebar_1',
                        'size': '300x250',
                        'after_widget': 2,  # After 2nd widget in right column
                        'column': 'right',
                    },
                    {
                        'position': 'left_sidebar_2',
                        'size': '300x600',  # Half page
                        'after_widget': 4,
                        'column': 'left',
                    },
                    {
                        'position': 'bottom_banner',
                        'size': '728x90',
                        'after_widget': 'last',  # After all widgets
                        'column': 'full',
                    },
                ]
            
            # Map to actual ad units
            # Note: AdPlacement model doesn't have position field, using slug instead
            for slot in slots:
                matching_placement = placements.filter(
                    slug__icontains=slot['position'].replace('_', '-')
                ).first()
                
                if matching_placement:
                    slot['ad_unit'] = {
                        'id': matching_placement.id,
                        'code': matching_placement.code if hasattr(matching_placement, 'code') else '',
                        'provider': 'custom',
                    }
            
            return {
                'slots': slots,
                'auto_refresh': True,
                'refresh_interval': 30,  # seconds
            }
            
        except Exception as e:
            logger.error(f"Error getting ad placements: {e}")
            return {'slots': []}
    
    # === COMBINED WIDGET DATA ===
    
    @classmethod
    def get_homepage_data(cls, config: Optional[Dict] = None) -> Dict:
        """
        Get all homepage widget data in single call - optimized for page load
        
        Args:
            config: Optional dict with limits per widget type
                {
                    'latest_firmwares': 10,
                    'trending_firmwares': 10,
                    'latest_blogs': 8,
                    'trending_blogs': 8,
                    'most_requested': 10,
                }
        
        Returns:
            Dict with all widget data + ad placements
        """
        config = config or {}
        
        return {
            'latest_firmwares': cls.get_latest_firmwares(
                limit=config.get('latest_firmwares', 10)
            ),
            'trending_firmwares': cls.get_trending_firmwares(
                limit=config.get('trending_firmwares', 10),
                days=config.get('trending_days', 7)
            ),
            'most_requested_firmwares': cls.get_most_requested_firmwares(
                limit=config.get('most_requested', 10)
            ),
            'latest_blogs': cls.get_latest_blogs(
                limit=config.get('latest_blogs', 8)
            ),
            'trending_blogs': cls.get_trending_blogs(
                limit=config.get('trending_blogs', 8),
                days=config.get('trending_blog_days', 7)
            ),
            'ad_placements': cls.get_ad_placements(
                page_layout=config.get('layout', 'dual_column')
            ),
            'cache_timestamp': timezone.now().isoformat(),
        }
    
    # === CACHE INVALIDATION ===
    
    @classmethod
    def invalidate_caches(cls, widget_types: Optional[List[str]] = None):
        """
        Invalidate specific widget caches (call via signals when content updates)
        
        Args:
            widget_types: List of widget types to invalidate, or None for all
        """
        if widget_types is None:
            widget_types = [
                'latest_firmwares', 'trending_firmwares', 'most_requested',
                'latest_blogs', 'trending_blogs'
            ]
        
        patterns = {
            'latest_firmwares': 'homepage_latest_firmwares_*',
            'trending_firmwares': 'homepage_trending_firmwares_*',
            'most_requested': 'homepage_most_requested_*',
            'latest_blogs': 'homepage_latest_blogs_*',
            'trending_blogs': 'homepage_trending_blogs_*',
        }
        
        for widget_type in widget_types:
            pattern = patterns.get(widget_type)
            if pattern:
                # Django cache doesn't support pattern deletion natively
                # Clear specific common keys
                for limit in [5, 8, 10, 15, 20]:
                    cache_key = pattern.replace('*', str(limit))
                    cache.delete(cache_key)
                
                logger.info(f"Invalidated cache for {widget_type}")
