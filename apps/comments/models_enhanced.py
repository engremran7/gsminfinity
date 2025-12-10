"""
Enhanced Comment models with enterprise-grade features.
Includes reactions, voting, threading, moderation, analytics, and gamification.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, F, Count, Avg

from apps.core.models import TimestampedModel, SoftDeleteModel


class CommentReaction(TimestampedModel):
    """
    User reactions to comments (like, love, insightful, funny, etc.)
    Replaces simple up/down voting with rich emotional responses.
    """
    class ReactionType(models.TextChoices):
        LIKE = "like", "👍 Like"
        LOVE = "love", "❤️ Love"
        INSIGHTFUL = "insightful", "💡 Insightful"
        FUNNY = "funny", "😂 Funny"
        CELEBRATE = "celebrate", "🎉 Celebrate"
        SUPPORT = "support", "🙌 Support"
        CURIOUS = "curious", "🤔 Curious"
        DISAGREE = "disagree", "👎 Disagree"

    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="reactions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_reactions"
    )
    reaction_type = models.CharField(
        max_length=20,
        choices=ReactionType.choices,
        default=ReactionType.LIKE
    )
    
    class Meta:
        unique_together = [["comment", "user"]]
        indexes = [
            models.Index(fields=["comment", "reaction_type"]),
            models.Index(fields=["user", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.user} → {self.get_reaction_type_display()} on comment {self.comment_id}"


class CommentVote(TimestampedModel):
    """
    Traditional up/down voting system (alternative to reactions).
    Provides karma/reputation scoring.
    """
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="votes"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_votes"
    )
    vote = models.SmallIntegerField(
        choices=[(-1, "Downvote"), (1, "Upvote")],
        validators=[MinValueValidator(-1), MaxValueValidator(1)]
    )
    
    class Meta:
        unique_together = [["comment", "user"]]
        indexes = [
            models.Index(fields=["comment", "vote"]),
        ]
    
    def __str__(self) -> str:
        direction = "upvoted" if self.vote > 0 else "downvoted"
        return f"{self.user} {direction} comment {self.comment_id}"


class CommentFlag(TimestampedModel):
    """
    User-generated flags for inappropriate content.
    Triggers moderation workflow when threshold is reached.
    """
    class FlagReason(models.TextChoices):
        SPAM = "spam", "Spam"
        HARASSMENT = "harassment", "Harassment"
        HATE_SPEECH = "hate_speech", "Hate Speech"
        OFF_TOPIC = "off_topic", "Off Topic"
        MISINFORMATION = "misinformation", "Misinformation"
        NSFW = "nsfw", "NSFW Content"
        OTHER = "other", "Other"
    
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="flags"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_flags"
    )
    reason = models.CharField(max_length=30, choices=FlagReason.choices)
    details = models.TextField(blank=True, default="")
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_flags"
    )
    
    class Meta:
        unique_together = [["comment", "user"]]
        indexes = [
            models.Index(fields=["comment", "resolved"]),
            models.Index(fields=["reason", "resolved"]),
        ]
    
    def __str__(self) -> str:
        return f"Flag by {self.user} on comment {self.comment_id}: {self.reason}"


class CommentMention(TimestampedModel):
    """
    Track @mentions in comments for notifications.
    """
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="mentions"
    )
    mentioned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_mentions"
    )
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [["comment", "mentioned_user"]]
        indexes = [
            models.Index(fields=["mentioned_user", "notified"]),
        ]
    
    def __str__(self) -> str:
        return f"@{self.mentioned_user} mentioned in comment {self.comment_id}"


class CommentEdit(TimestampedModel):
    """
    Track comment edit history for transparency and moderation.
    """
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="edit_history"
    )
    previous_body = models.TextField()
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_edits"
    )
    edit_reason = models.CharField(max_length=200, blank=True, default="")
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["comment", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"Edit to comment {self.comment_id} at {self.created_at}"


class CommentBookmark(TimestampedModel):
    """
    Allow users to bookmark comments for later reference.
    """
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarked_comments"
    )
    notes = models.TextField(blank=True, default="", help_text="Personal notes about this bookmark")
    
    class Meta:
        unique_together = [["comment", "user"]]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.user} bookmarked comment {self.comment_id}"


class CommentAward(TimestampedModel):
    """
    Awards/badges given to exceptional comments.
    Gamification element to encourage quality contributions.
    """
    class AwardType(models.TextChoices):
        GOLD = "gold", "🥇 Gold"
        SILVER = "silver", "🥈 Silver"
        BRONZE = "bronze", "🥉 Bronze"
        HELPFUL = "helpful", "✨ Helpful"
        INSIGHTFUL = "insightful", "💎 Insightful"
        EXPERT = "expert", "👨‍🎓 Expert"
        POPULAR = "popular", "🔥 Popular"
        TRENDING = "trending", "📈 Trending"
    
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="awards"
    )
    award_type = models.CharField(max_length=20, choices=AwardType.choices)
    given_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="awards_given"
    )
    auto_assigned = models.BooleanField(default=False, help_text="Auto-assigned by system based on metrics")
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["comment", "award_type"]),
            models.Index(fields=["given_by", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_award_type_display()} award for comment {self.comment_id}"


class CommentAnalytics(models.Model):
    """
    Aggregated analytics for comments.
    Updated periodically for performance.
    """
    comment = models.OneToOneField(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="analytics",
        primary_key=True
    )
    views = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    upvotes = models.PositiveIntegerField(default=0)
    downvotes = models.PositiveIntegerField(default=0)
    net_votes = models.IntegerField(default=0)
    reaction_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    flag_count = models.PositiveIntegerField(default=0)
    bookmark_count = models.PositiveIntegerField(default=0)
    award_count = models.PositiveIntegerField(default=0)
    engagement_score = models.FloatField(default=0.0, help_text="Calculated engagement metric")
    quality_score = models.FloatField(default=0.0, help_text="AI-calculated quality score")
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["-engagement_score"]),
            models.Index(fields=["-quality_score"]),
            models.Index(fields=["-net_votes"]),
        ]
    
    def calculate_engagement_score(self):
        """Calculate composite engagement score."""
        score = (
            self.upvotes * 2 +
            self.reaction_count * 1.5 +
            self.reply_count * 3 +
            self.bookmark_count * 5 +
            self.award_count * 10 -
            self.downvotes * 1 -
            self.flag_count * 5
        )
        self.engagement_score = max(0, score)
        self.net_votes = self.upvotes - self.downvotes
        return self.engagement_score
    
    def __str__(self) -> str:
        return f"Analytics for comment {self.comment_id}: {self.engagement_score:.1f} engagement"


class CommentThread(TimestampedModel):
    """
    Materialized thread metadata for performance.
    Denormalizes thread structure for fast queries.
    """
    root_comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        related_name="thread_metadata"
    )
    total_replies = models.PositiveIntegerField(default=0)
    max_depth = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    participant_count = models.PositiveIntegerField(default=1)
    is_locked = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=["-last_activity"]),
            models.Index(fields=["is_featured", "-last_activity"]),
        ]
    
    def __str__(self) -> str:
        return f"Thread {self.root_comment_id}: {self.total_replies} replies"


class ModerationAction(TimestampedModel):
    """
    Audit log of all moderation actions.
    Provides transparency and accountability.
    """
    class ActionType(models.TextChoices):
        APPROVE = "approve", "Approved"
        REJECT = "reject", "Rejected"
        DELETE = "delete", "Deleted"
        EDIT = "edit", "Edited"
        LOCK = "lock", "Locked"
        UNLOCK = "unlock", "Unlocked"
        WARN_USER = "warn_user", "Warned User"
        BAN_USER = "ban_user", "Banned User"
        UNBAN_USER = "unban_user", "Unbanned User"
        MARK_SPAM = "mark_spam", "Marked as Spam"
    
    comment = models.ForeignKey(
        "comments.Comment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="moderation_actions"
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="moderation_actions"
    )
    reason = models.TextField(blank=True, default="")
    auto_moderated = models.BooleanField(default=False, help_text="Action taken by AI/automation")
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["comment", "-created_at"]),
            models.Index(fields=["moderator", "-created_at"]),
            models.Index(fields=["action", "-created_at"]),
        ]
    
    def __str__(self) -> str:
        mod = "Auto" if self.auto_moderated else str(self.moderator)
        return f"{mod}: {self.get_action_display()} at {self.created_at}"
