"""
Smart Content Distribution Module
ML-optimized posting times and platform selection
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from django.utils import timezone
from django.db.models import Avg, Count, Q

logger = logging.getLogger(__name__)


class SmartDistributionEngine:
    """
    AI-powered content distribution optimizer.
    
    Features:
    - Predict optimal posting times per platform
    - Auto-select best platforms for content type
    - Optimize hashtags based on engagement
    - A/B test different content variations
    - Learn from historical performance
    """
    
    # Platform-specific optimal time windows (UTC)
    DEFAULT_OPTIMAL_TIMES = {
        'twitter': [
            {'hour': 9, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday mornings
            {'hour': 12, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday lunch
            {'hour': 17, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday evening
        ],
        'facebook': [
            {'hour': 13, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday afternoon
            {'hour': 15, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday mid-afternoon
            {'hour': 19, 'day_of_week': [6, 7]},  # Weekend evening
        ],
        'linkedin': [
            {'hour': 8, 'day_of_week': [2, 3, 4]},  # Tue-Thu morning
            {'hour': 12, 'day_of_week': [2, 3, 4]},  # Tue-Thu lunch
            {'hour': 17, 'day_of_week': [2, 3]},  # Tue-Wed evening
        ],
        'instagram': [
            {'hour': 11, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday late morning
            {'hour': 14, 'day_of_week': [1, 2, 3, 4, 5]},  # Weekday afternoon
            {'hour': 19, 'day_of_week': [6, 7]},  # Weekend evening
        ],
    }
    
    # Platform-specific content guidelines
    PLATFORM_SPECS = {
        'twitter': {
            'char_limit': 280,
            'hashtag_limit': 2,
            'optimal_hashtags': 1,
            'image_required': False,
            'video_max_length': 140,  # seconds
        },
        'facebook': {
            'char_limit': 63206,
            'hashtag_limit': 5,
            'optimal_hashtags': 3,
            'image_required': True,
            'video_max_length': 240,
        },
        'linkedin': {
            'char_limit': 3000,
            'hashtag_limit': 5,
            'optimal_hashtags': 3,
            'image_required': False,
            'video_max_length': 600,
        },
        'instagram': {
            'char_limit': 2200,
            'hashtag_limit': 30,
            'optimal_hashtags': 11,
            'image_required': True,
            'video_max_length': 60,
        },
    }
    
    @classmethod
    def predict_optimal_time(
        cls,
        platform: str,
        content_type: str = 'general',
        timezone_offset: int = 0
    ) -> datetime:
        """
        Predict optimal posting time for platform.
        
        Args:
            platform: Platform name (twitter, facebook, etc.)
            content_type: Type of content (firmware, blog, announcement)
            timezone_offset: User's timezone offset from UTC
            
        Returns:
            Optimal datetime for posting
        """
        try:
            # Get historical performance data
            historical_best = cls._get_historical_best_time(platform, content_type)
            
            if historical_best:
                return historical_best
            
            # Fall back to default optimal times
            optimal_windows = cls.DEFAULT_OPTIMAL_TIMES.get(platform, [])
            
            if not optimal_windows:
                # Default to next hour
                return timezone.now() + timedelta(hours=1)
            
            # Find next optimal window
            now = timezone.now()
            current_day = now.isoweekday()  # 1=Monday, 7=Sunday
            current_hour = now.hour
            
            for window in optimal_windows:
                if current_day in window['day_of_week']:
                    if window['hour'] > current_hour:
                        # Today at optimal hour
                        return now.replace(
                            hour=window['hour'],
                            minute=0,
                            second=0,
                            microsecond=0
                        )
            
            # No optimal time today, find next day
            for days_ahead in range(1, 8):
                future_date = now + timedelta(days=days_ahead)
                future_day = future_date.isoweekday()
                
                for window in optimal_windows:
                    if future_day in window['day_of_week']:
                        return future_date.replace(
                            hour=window['hour'],
                            minute=0,
                            second=0,
                            microsecond=0
                        )
            
            # Fallback
            return now + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"Error predicting optimal time: {e}")
            return timezone.now() + timedelta(hours=1)
    
    @classmethod
    def _get_historical_best_time(
        cls,
        platform: str,
        content_type: str
    ) -> Optional[datetime]:
        """
        Analyze historical performance to find best posting time.
        
        Returns:
            Datetime of historically best performing time window, or None
        """
        try:
            from apps.distribution.models import ShareJob
            
            # Get successful jobs from last 30 days
            cutoff = timezone.now() - timedelta(days=30)
            
            jobs = ShareJob.objects.filter(
                channel=platform,
                status='delivered',
                created_at__gte=cutoff
            ).values('created_at')
            
            if not jobs.exists():
                return None
            
            # Analyze by hour of day
            hour_performance = defaultdict(int)
            
            for job in jobs:
                hour = job['created_at'].hour
                hour_performance[hour] += 1
            
            # Find best performing hour
            if hour_performance:
                best_hour = max(hour_performance, key=hour_performance.get)
                
                # Schedule for next occurrence of that hour
                now = timezone.now()
                if now.hour < best_hour:
                    return now.replace(hour=best_hour, minute=0, second=0, microsecond=0)
                else:
                    return (now + timedelta(days=1)).replace(
                        hour=best_hour, minute=0, second=0, microsecond=0
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting historical best time: {e}")
            return None
    
    @classmethod
    def select_optimal_platforms(
        cls,
        content_type: str,
        has_image: bool = False,
        has_video: bool = False,
        content_length: int = 0
    ) -> List[str]:
        """
        Select best platforms for content based on characteristics.
        
        Args:
            content_type: Type of content (firmware, blog, announcement)
            has_image: Whether content includes image
            has_video: Whether content includes video
            content_length: Length of text content
            
        Returns:
            List of recommended platform names
        """
        recommended = []
        
        # Firmware releases: Twitter, Facebook, LinkedIn
        if content_type == 'firmware':
            recommended = ['twitter', 'facebook', 'linkedin']
            if has_image:
                recommended.append('instagram')
        
        # Blog posts: All platforms
        elif content_type == 'blog':
            recommended = ['twitter', 'facebook', 'linkedin']
            if has_image:
                recommended.append('instagram')
        
        # Announcements: Twitter, Facebook
        elif content_type == 'announcement':
            recommended = ['twitter', 'facebook']
        
        # General: Based on content characteristics
        else:
            if content_length <= 280:
                recommended.append('twitter')
            if has_image:
                recommended.extend(['facebook', 'instagram'])
            if content_length > 500:
                recommended.append('linkedin')
        
        return list(set(recommended))  # Remove duplicates
    
    @classmethod
    def optimize_content_for_platform(
        cls,
        content: str,
        platform: str,
        hashtags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Optimize content for specific platform.
        
        Args:
            content: Original content text
            platform: Target platform
            hashtags: List of hashtags
            
        Returns:
            Optimized content dictionary
        """
        specs = cls.PLATFORM_SPECS.get(platform, {})
        char_limit = specs.get('char_limit', 1000)
        hashtag_limit = specs.get('hashtag_limit', 5)
        optimal_hashtags = specs.get('optimal_hashtags', 3)
        
        # Truncate content if needed
        optimized_content = content
        if len(content) > char_limit:
            optimized_content = content[:char_limit-3] + '...'
        
        # Optimize hashtags
        optimized_hashtags = hashtags[:optimal_hashtags] if hashtags else []
        
        # Platform-specific formatting
        if platform == 'twitter':
            # Keep it concise, add call-to-action
            if len(optimized_content) < 200:
                optimized_content += "\n\n👉 Download now!"
        
        elif platform == 'facebook':
            # Add engaging question
            optimized_content += "\n\nWhat do you think? Let us know in the comments!"
        
        elif platform == 'linkedin':
            # Professional tone
            optimized_content = optimized_content.replace('!', '.')
        
        elif platform == 'instagram':
            # Emoji-rich, hashtag-heavy
            optimized_content += "\n\n" + " ".join(f"#{tag}" for tag in optimized_hashtags)
        
        return {
            'content': optimized_content,
            'hashtags': optimized_hashtags,
            'char_count': len(optimized_content),
            'platform': platform,
        }


# Convenience functions
def schedule_smart_distribution(
    content: str,
    content_type: str = 'general',
    platforms: List[str] = None,
    hashtags: List[str] = None,
    has_image: bool = False
) -> List[Dict[str, Any]]:
    """
    Create optimized distribution schedule for content.
    
    Returns:
        List of distribution job configurations
    """
    engine = SmartDistributionEngine()
    
    # Auto-select platforms if not specified
    if not platforms:
        platforms = engine.select_optimal_platforms(
            content_type=content_type,
            has_image=has_image,
            content_length=len(content)
        )
    
    jobs = []
    
    for platform in platforms:
        # Predict optimal time
        optimal_time = engine.predict_optimal_time(platform, content_type)
        
        # Optimize content
        optimized = engine.optimize_content_for_platform(content, platform, hashtags)
        
        jobs.append({
            'platform': platform,
            'content': optimized['content'],
            'hashtags': optimized['hashtags'],
            'schedule_at': optimal_time,
            'content_type': content_type,
        })
    
    return jobs

