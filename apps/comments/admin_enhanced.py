"""
Django admin registration for enhanced Comment models.
Provides full admin interface for all comment features.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from apps.comments.models import Comment, CommentSettings
from apps.comments.models_enhanced import (
    CommentReaction, CommentVote, CommentFlag, CommentMention,
    CommentEdit, CommentBookmark, CommentAward, CommentAnalytics,
    CommentThread, ModerationAction
)


@admin.register(CommentReaction)
class CommentReactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'user', 'reaction_type', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['comment__body', 'user__username']
    raw_id_fields = ['comment', 'user']
    date_hierarchy = 'created_at'
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentVote)
class CommentVoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'user', 'vote_display', 'created_at']
    list_filter = ['vote', 'created_at']
    search_fields = ['comment__body', 'user__username']
    raw_id_fields = ['comment', 'user']
    date_hierarchy = 'created_at'
    
    def vote_display(self, obj):
        if obj.vote > 0:
            return format_html('<span style="color: green;">⬆ Upvote</span>')
        return format_html('<span style="color: red;">⬇ Downvote</span>')
    vote_display.short_description = 'Vote'
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentFlag)
class CommentFlagAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'user', 'reason', 'resolved', 'created_at']
    list_filter = ['reason', 'resolved', 'created_at']
    search_fields = ['comment__body', 'user__username', 'details']
    raw_id_fields = ['comment', 'user', 'resolved_by']
    date_hierarchy = 'created_at'
    actions = ['mark_resolved']
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'
    
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            resolved=True,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f'{updated} flags marked as resolved.')
    mark_resolved.short_description = 'Mark selected flags as resolved'


@admin.register(CommentMention)
class CommentMentionAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'mentioned_user', 'notified', 'created_at']
    list_filter = ['notified', 'created_at']
    search_fields = ['comment__body', 'mentioned_user__username']
    raw_id_fields = ['comment', 'mentioned_user']
    date_hierarchy = 'created_at'
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentEdit)
class CommentEditAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'edited_by', 'edit_reason', 'created_at']
    list_filter = ['created_at']
    search_fields = ['comment__body', 'edited_by__username', 'edit_reason']
    raw_id_fields = ['comment', 'edited_by']
    date_hierarchy = 'created_at'
    readonly_fields = ['previous_body']
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentBookmark)
class CommentBookmarkAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['comment__body', 'user__username', 'notes']
    raw_id_fields = ['comment', 'user']
    date_hierarchy = 'created_at'
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentAward)
class CommentAwardAdmin(admin.ModelAdmin):
    list_display = ['id', 'comment_link', 'award_type_display', 'given_by', 'auto_assigned', 'created_at']
    list_filter = ['award_type', 'auto_assigned', 'created_at']
    search_fields = ['comment__body']
    raw_id_fields = ['comment', 'given_by']
    date_hierarchy = 'created_at'
    
    def award_type_display(self, obj):
        icons = {
            'gold': '🥇',
            'silver': '🥈',
            'bronze': '🥉',
            'helpful': '✨',
            'insightful': '💎',
            'expert': '👨‍🎓',
            'popular': '🔥',
            'trending': '📈',
        }
        icon = icons.get(obj.award_type, '')
        return format_html('{} {}', icon, obj.get_award_type_display())
    award_type_display.short_description = 'Award'
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentAnalytics)
class CommentAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'comment_link', 'engagement_score', 'quality_score', 
        'upvotes', 'downvotes', 'reaction_count', 'reply_count',
        'last_calculated'
    ]
    list_filter = ['last_calculated']
    search_fields = ['comment__body']
    readonly_fields = [
        'views', 'unique_viewers', 'upvotes', 'downvotes', 'net_votes',
        'reaction_count', 'reply_count', 'flag_count', 'bookmark_count',
        'award_count', 'engagement_score', 'quality_score', 'last_calculated'
    ]
    
    def comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
    comment_link.short_description = 'Comment'


@admin.register(CommentThread)
class CommentThreadAdmin(admin.ModelAdmin):
    list_display = [
        'root_comment_link', 'total_replies', 'max_depth',
        'participant_count', 'is_locked', 'is_featured', 'last_activity'
    ]
    list_filter = ['is_locked', 'is_featured', 'last_activity']
    search_fields = ['root_comment__body']
    raw_id_fields = ['root_comment']
    date_hierarchy = 'last_activity'
    actions = ['lock_threads', 'unlock_threads', 'mark_featured']
    
    def root_comment_link(self, obj):
        url = reverse('admin:comments_comment_change', args=[obj.root_comment_id])
        return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.root_comment_id}")
    root_comment_link.short_description = 'Root Comment'
    
    def lock_threads(self, request, queryset):
        updated = queryset.update(is_locked=True)
        self.message_user(request, f'{updated} threads locked.')
    lock_threads.short_description = 'Lock selected threads'
    
    def unlock_threads(self, request, queryset):
        updated = queryset.update(is_locked=False)
        self.message_user(request, f'{updated} threads unlocked.')
    unlock_threads.short_description = 'Unlock selected threads'
    
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} threads marked as featured.')
    mark_featured.short_description = 'Mark as featured'


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'comment_link', 'action', 'moderator',
        'auto_moderated', 'created_at'
    ]
    list_filter = ['action', 'auto_moderated', 'created_at']
    search_fields = ['comment__body', 'moderator__username', 'reason']
    raw_id_fields = ['comment', 'moderator']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    def comment_link(self, obj):
        if obj.comment:
            url = reverse('admin:comments_comment_change', args=[obj.comment_id])
            return format_html('<a href="{}">{}</a>', url, f"Comment #{obj.comment_id}")
        return '-'
    comment_link.short_description = 'Comment'
