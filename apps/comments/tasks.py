"""
Celery/Django-Q tasks for comment operations.
Background processing for moderation, notifications, and analytics.
"""
from __future__ import annotations

import logging
from typing import Optional
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from django.utils import timezone

from django.utils import timezone

from apps.comments.models import Comment
from apps.comments.services.comment_service import CommentService
from apps.comments.services.moderation import classify_comment

logger = logging.getLogger(__name__)
User = get_user_model()


def moderate_comment(comment_id: int):
    """
    AI moderation task for new comments.
    """
    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        logger.error(f"Comment {comment_id} not found for moderation")
        return
    
    # Classify comment
    result = classify_comment(comment.body)
    
    # Update comment
    comment.toxicity_score = result.toxicity_score
    comment.moderation_flags = {
        "label": result.label,
        "score": result.score,
        "rationale": result.rationale,
        "toxicity_score": result.toxicity_score,
        "spam_score": result.spam_score,
        "hate_score": result.hate_score,
    }
    
    # Auto-approve or reject based on classification
    if result.label == "approved" and result.toxicity_score < 0.3:
        comment.status = Comment.Status.APPROVED
        comment.is_approved = True
    elif result.label in ["rejected", "spam"] or result.toxicity_score > 0.7:
        comment.status = Comment.Status.REJECTED
    
    comment.save()
    
    logger.info(f"Comment {comment_id} moderated: {result.label} (toxicity: {result.toxicity_score})")


def remoderate_comment(comment_id: int):
    """
    Re-moderate edited comment.
    """
    moderate_comment(comment_id)  # Same logic


def update_comment_analytics(comment_id: int):
    """
    Update analytics for comment.
    """
    service = CommentService()
    service.update_comment_analytics(comment_id)


def notify_comment_reaction(comment_id: int, user_id: int, reaction_type: str):
    """
    Notify comment author about reaction.
    """
    try:
        comment = Comment.objects.select_related("user").get(id=comment_id)
        user = User.objects.get(id=user_id)
    except (Comment.DoesNotExist, User.DoesNotExist):
        return
    
    # Don't notify self-reactions
    if comment.user_id == user_id:
        return
    
    # Send email notification
    subject = f"New reaction on your comment"
    message = f"{user.username} reacted with {reaction_type} to your comment:\n\n{comment.body[:200]}"
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [comment.user.email],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send reaction notification: {e}")


def notify_comment_award(comment_id: int, award_type: str):
    """
    Notify comment author about award.
    """
    try:
        comment = Comment.objects.select_related("user").get(id=comment_id)
    except Comment.DoesNotExist:
        return
    
    subject = f"Your comment received an award!"
    message = f"Congratulations! Your comment received the {award_type} award:\n\n{comment.body[:200]}"
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [comment.user.email],
            fail_silently=True
        )
    except Exception as e:
        logger.error(f"Failed to send award notification: {e}")


def notify_mention(comment_id: int, user_id: int):
    """
    Notify user they were mentioned in comment.
    """
    try:
        comment = Comment.objects.select_related("user").get(id=comment_id)
        mentioned_user = User.objects.get(id=user_id)
    except (Comment.DoesNotExist, User.DoesNotExist):
        return
    
    subject = f"{comment.user.username} mentioned you in a comment"
    message = f"You were mentioned in a comment:\n\n{comment.body[:200]}"
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [mentioned_user.email],
            fail_silently=True
        )
        
        # Mark as notified
        from apps.comments.models_enhanced import CommentMention
        CommentMention.objects.filter(
            comment=comment,
            mentioned_user=mentioned_user
        ).update(notified=True, notified_at=timezone.now())
        
    except Exception as e:
        logger.error(f"Failed to send mention notification: {e}")
