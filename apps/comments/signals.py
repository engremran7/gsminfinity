"""
Enhanced notification signals for comment interactions.
Sends notifications for replies, mentions, reactions, and moderation actions.
"""

from __future__ import annotations

import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apps.users.services.notifications import send_notification, notifications_enabled

logger = logging.getLogger(__name__)


@receiver(post_save, sender='comments.Comment')
def notify_on_comment(sender, instance, created, **kwargs):
    """
    Send notifications when:
    - Someone comments on a post (notify post author)
    - Someone replies to a comment (notify parent comment author)
    """
    if not created or not notifications_enabled():
        return
    
    try:
        # Don't notify if comment is pending or spam
        if instance.status in ['pending', 'spam']:
            return
        
        # Notify post author when someone comments
        if instance.post and instance.post.author != instance.user:
            send_notification(
                recipient=instance.post.author,
                title="New comment on your post",
                message=f"{instance.user.get_full_name()} commented on \"{instance.post.title}\"",
                level="info",
                url=instance.post.get_absolute_url() + f"#comment-{instance.pk}",
                actor=instance.user,
                channel="web",
                action_type="comment",
                icon="comment",
            )
        
        # Notify parent comment author when someone replies
        if instance.parent and instance.parent.user != instance.user:
            send_notification(
                recipient=instance.parent.user,
                title="New reply to your comment",
                message=f"{instance.user.get_full_name()} replied to your comment",
                level="info",
                url=(instance.post.get_absolute_url() if instance.post else "#") + f"#comment-{instance.pk}",
                actor=instance.user,
                channel="web",
                action_type="reply",
                icon="reply",
            )
    except Exception as exc:
        logger.exception("Failed to send comment notification: %s", exc)


@receiver(post_save, sender='comments.CommentReaction')
def notify_on_reaction(sender, instance, created, **kwargs):
    """Notify comment author when someone reacts to their comment."""
    if not created or not notifications_enabled():
        return
    
    try:
        comment = instance.comment
        if comment.user != instance.user:
            reaction_emoji = {
                'like': '👍',
                'love': '❤️',
                'insight': '💡',
                'laugh': '😄',
                'celebrate': '🎉',
                'pray': '🙏',
                'curious': '🤔',
                'dislike': '👎',
            }.get(instance.reaction_type, '👍')
            
            send_notification(
                recipient=comment.user,
                title="New reaction on your comment",
                message=f"{instance.user.get_full_name()} reacted {reaction_emoji} to your comment",
                level="info",
                url=(comment.post.get_absolute_url() if comment.post else "#") + f"#comment-{comment.pk}",
                actor=instance.user,
                channel="web",
                action_type="reaction",
                icon="heart",
            )
    except Exception as exc:
        logger.exception("Failed to send reaction notification: %s", exc)


@receiver(post_save, sender='comments.CommentVote')
def notify_on_vote(sender, instance, created, **kwargs):
    """Notify comment author when their comment gets upvoted."""
    if not created or not notifications_enabled():
        return
    
    try:
        comment = instance.comment
        if comment.user != instance.user and instance.vote_type == 'up':
            send_notification(
                recipient=comment.user,
                title="Your comment was upvoted",
                message=f"{instance.user.get_full_name()} upvoted your comment",
                level="info",
                url=(comment.post.get_absolute_url() if comment.post else "#") + f"#comment-{comment.pk}",
                actor=instance.user,
                channel="web",
                action_type="vote",
                icon="chevron-up",
            )
    except Exception as exc:
        logger.exception("Failed to send vote notification: %s", exc)


@receiver(post_save, sender='comments.CommentMention')
def notify_on_mention(sender, instance, created, **kwargs):
    """Notify user when they're mentioned in a comment."""
    if not created or not notifications_enabled():
        return
    
    try:
        comment = instance.comment
        send_notification(
            recipient=instance.mentioned_user,
            title="You were mentioned in a comment",
            message=f"{comment.user.get_full_name()} mentioned you in a comment",
            level="info",
            url=(comment.post.get_absolute_url() if comment.post else "#") + f"#comment-{comment.pk}",
            actor=comment.user,
            channel="web",
            action_type="mention",
            icon="at-sign",
        )
    except Exception as exc:
        logger.exception("Failed to send mention notification: %s", exc)


@receiver(post_save, sender='comments.CommentAward')
def notify_on_award(sender, instance, created, **kwargs):
    """Notify comment author when they receive an award."""
    if not created or not notifications_enabled():
        return
    
    try:
        comment = instance.comment
        if comment.user != instance.awarded_by:
            award_emoji = {
                'gold': '🏆',
                'silver': '🥈',
                'bronze': '🥉',
                'helpful': '✨',
                'insightful': '💡',
                'funny': '😂',
            }.get(instance.award_type, '🏅')
            
            send_notification(
                recipient=comment.user,
                title=f"You received a {instance.award_type} award!",
                message=f"{instance.awarded_by.get_full_name()} awarded your comment {award_emoji}",
                level="info",
                url=(comment.post.get_absolute_url() if comment.post else "#") + f"#comment-{comment.pk}",
                actor=instance.awarded_by,
                channel="web",
                action_type="award",
                icon="award",
            )
    except Exception as exc:
        logger.exception("Failed to send award notification: %s", exc)


@receiver(post_save, sender='comments.ModerationAction')
def notify_on_moderation(sender, instance, created, **kwargs):
    """Notify comment author about moderation actions."""
    if not created or not notifications_enabled():
        return
    
    try:
        comment = instance.comment
        action_messages = {
            'approved': 'Your comment has been approved',
            'rejected': 'Your comment was not approved',
            'flagged': 'Your comment has been flagged for review',
            'hidden': 'Your comment has been hidden',
            'deleted': 'Your comment has been removed',
        }
        
        level = 'warning' if instance.action in ['rejected', 'flagged', 'hidden', 'deleted'] else 'info'
        
        send_notification(
            recipient=comment.user,
            title="Comment moderation update",
            message=action_messages.get(instance.action, f"Action taken on your comment: {instance.action}"),
            level=level,
            url=(comment.post.get_absolute_url() if comment.post else "#") + f"#comment-{comment.pk}",
            actor=instance.moderator,
            channel="web",
            action_type="moderation",
            icon="flag",
        )
    except Exception as exc:
        logger.exception("Failed to send moderation notification: %s", exc)
