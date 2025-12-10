
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from solo.models import SingletonModel
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from apps.core.models import TimestampedModel, SoftDeleteModel

# Import enhanced models for migrations
from apps.comments.models_enhanced import (
    CommentReaction, CommentVote, CommentFlag, CommentMention,
    CommentEdit, CommentBookmark, CommentAward, CommentAnalytics,
    CommentThread, ModerationAction
)


class Comment(TimestampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SPAM = "spam", "Spam"

    # Generic target to support comments on any model; keep post for backward compatibility.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")
    post = models.ForeignKey(
        "blog.Post",
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    body = models.TextField(
        validators=[MinLengthValidator(3), MaxLengthValidator(5000)],
        help_text="Plain text or sanitized HTML from editor; capped to 5k chars.",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Auto-set when moderation marks approved.",
    )
    score = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    moderation_flags = models.JSONField(default=dict, blank=True)
    toxicity_score = models.FloatField(default=0.0)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "status"]),
        ]

    def __str__(self) -> str:
        target = self.post or self.content_object or "unknown"
        return f"Comment by {self.user} on {target}"

    def save(self, *args, **kwargs):
        """
        Keep generic target in sync with legacy post FK to support gradual migration.
        """
        if self.post and not (self.content_type and self.object_id):
            try:
                self.content_type = ContentType.objects.get_for_model(self.post)
                self.object_id = self.post.pk
            except Exception:
                pass
        if self.status == self.Status.APPROVED and not self.is_approved:
            self.is_approved = True
        super().save(*args, **kwargs)


class CommentSettings(SingletonModel):
    """
    Per-app settings for comments so this module can be reused.
    """

    enable_comments = models.BooleanField(default=True)
    allow_anonymous = models.BooleanField(default=False)
    enable_ai_moderation = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Comment Settings"

    def __str__(self) -> str:
        return "Comment Settings"


