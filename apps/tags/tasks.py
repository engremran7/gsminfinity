"""
Celery/Django-Q tasks for tag operations.
Background processing for analytics, trending, and notifications.
"""
from __future__ import annotations

import logging
from typing import Optional
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tags.models import Tag
from apps.tags.services.tag_service import TagService

logger = logging.getLogger(__name__)
User = get_user_model()


def update_trending_tags_hourly():
    """
    Update hourly trending tags.
    Run every hour via cron/celery beat.
    """
    service = TagService()
    service.update_trending_tags("hourly")
    logger.info("Updated hourly trending tags")


def update_trending_tags_daily():
    """
    Update daily trending tags.
    Run once per day via cron/celery beat.
    """
    service = TagService()
    service.update_trending_tags("daily")
    logger.info("Updated daily trending tags")


def update_trending_tags_weekly():
    """
    Update weekly trending tags.
    Run once per week via cron/celery beat.
    """
    service = TagService()
    service.update_trending_tags("weekly")
    logger.info("Updated weekly trending tags")


def update_trending_tags_monthly():
    """
    Update monthly trending tags.
    Run once per month via cron/celery beat.
    """
    service = TagService()
    service.update_trending_tags("monthly")
    logger.info("Updated monthly trending tags")


def update_tag_analytics(tag_id: int):
    """
    Update analytics for specific tag.
    """
    service = TagService()
    service.update_tag_analytics(tag_id)
    logger.info(f"Updated analytics for tag {tag_id}")


def update_all_tag_analytics():
    """
    Update analytics for all active tags.
    Run daily via cron/celery beat.
    """
    service = TagService()
    
    # Get all active tags
    tags = Tag.objects.filter(is_active=True, is_deleted=False)
    
    for tag in tags:
        try:
            service.update_tag_analytics(tag.id)
        except Exception as e:
            logger.error(f"Failed to update analytics for tag {tag.id}: {e}")
    
    logger.info(f"Updated analytics for {tags.count()} tags")


def discover_tag_relationships():
    """
    Discover related tags based on co-occurrence.
    Run weekly to find new relationships.
    """
    service = TagService()
    
    # Get popular tags
    tags = Tag.objects.filter(
        is_active=True,
        is_deleted=False,
        usage_count__gte=10
    ).order_by("-usage_count")[:100]
    
    relationships_created = 0
    
    for tag in tags:
        try:
            # Discover related tags
            related = service.discover_related_tags(tag, min_co_occurrence=3)
            
            # Create relationships
            for related_tag, count in related[:10]:  # Top 10
                strength = min(1.0, count / 10.0)  # Normalize to 0-1
                service.create_relationship(
                    from_tag=tag,
                    to_tag=related_tag,
                    relationship_type="related",
                    strength=strength
                )
                relationships_created += 1
                
        except Exception as e:
            logger.error(f"Failed to discover relationships for tag {tag.id}: {e}")
    
    logger.info(f"Discovered {relationships_created} tag relationships")


def notify_suggestion_approved(suggestion_id: int):
    """
    Notify user their tag suggestion was approved.
    """
    from apps.tags.models_enhanced import TagSuggestion
    
    try:
        suggestion = TagSuggestion.objects.select_related(
            "suggested_by", "created_tag"
        ).get(id=suggestion_id)
    except TagSuggestion.DoesNotExist:
        return
    
    if not suggestion.created_tag:
        return
    
    subject = f"Your tag suggestion was approved!"
    message = f"""Congratulations! Your tag suggestion '{suggestion.suggested_name}' has been approved and is now live.

You can view it here: [Tag URL]

Thank you for contributing to the community!
"""
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [suggestion.suggested_by.email],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send suggestion approval notification: {e}")


def send_tag_subscription_digest(user_id: int, frequency: str = "daily"):
    """
    Send digest of new content for subscribed tags.
    
    Args:
        user_id: User ID
        frequency: daily or weekly
    """
    from apps.tags.models_enhanced import TagSubscription
    from apps.tags.models_tagged_item import TaggedItem
    from datetime import timedelta
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return
    
    # Get user's subscriptions
    subscriptions = TagSubscription.objects.filter(
        user=user,
        is_active=True,
        notification_frequency=frequency
    ).select_related("tag")
    
    if not subscriptions:
        return
    
    # Calculate time window
    now = timezone.now()
    if frequency == "daily":
        since = now - timedelta(days=1)
    elif frequency == "weekly":
        since = now - timedelta(days=7)
    else:
        return
    
    # Collect new content for each subscribed tag
    digest_data = []
    
    for subscription in subscriptions:
        # Get recent tagged items
        new_items = TaggedItem.objects.filter(
            tag=subscription.tag,
            created_at__gte=since
        ).select_related("content_type")[:5]
        
        if new_items:
            digest_data.append({
                "tag": subscription.tag,
                "items": new_items
            })
    
    if not digest_data:
        return  # No new content
    
    # Build email
    subject = f"Your {frequency} tag digest"
    message = f"New content for your subscribed tags:\n\n"
    
    for data in digest_data:
        message += f"Tag: {data['tag'].name}\n"
        for item in data['items']:
            message += f"  - New {item.content_type.model}\n"
        message += "\n"
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send tag digest: {e}")


def send_daily_tag_digests():
    """
    Send daily digests to all users with daily subscriptions.
    Run once per day via cron/celery beat.
    """
    from apps.tags.models_enhanced import TagSubscription
    
    # Get all users with daily subscriptions
    user_ids = TagSubscription.objects.filter(
        is_active=True,
        notification_frequency="daily"
    ).values_list("user_id", flat=True).distinct()
    
    for user_id in user_ids:
        try:
            send_tag_subscription_digest(user_id, "daily")
        except Exception as e:
            logger.error(f"Failed to send daily digest to user {user_id}: {e}")
    
    logger.info(f"Sent daily digests to {len(user_ids)} users")


def send_weekly_tag_digests():
    """
    Send weekly digests to all users with weekly subscriptions.
    Run once per week via cron/celery beat.
    """
    from apps.tags.models_enhanced import TagSubscription
    
    # Get all users with weekly subscriptions
    user_ids = TagSubscription.objects.filter(
        is_active=True,
        notification_frequency="weekly"
    ).values_list("user_id", flat=True).distinct()
    
    for user_id in user_ids:
        try:
            send_tag_subscription_digest(user_id, "weekly")
        except Exception as e:
            logger.error(f"Failed to send weekly digest to user {user_id}: {e}")
    
    logger.info(f"Sent weekly digests to {len(user_ids)} users")
