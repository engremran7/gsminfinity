"""
Django admin registration for enhanced Tag models.
Provides full admin interface for all tag features.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count

from apps.tags.models import Tag, TagsSettings
from apps.tags.models_enhanced import (
    TagCategory, TagRelationship, TagTrending, TagAnalytics,
    TagSubscription, TagSuggestion, TagBlacklist, TagMerge,
    TagCollection, TagCollectionItem, TagAlias
)


@admin.register(TagCategory)
class TagCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color', 'icon', 'display_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']


@admin.register(TagRelationship)
class TagRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        'from_tag', 'relationship_type', 'to_tag',
        'strength', 'auto_generated', 'created_at'
    ]
    list_filter = ['relationship_type', 'auto_generated', 'created_at']
    search_fields = ['from_tag__name', 'to_tag__name']
    raw_id_fields = ['from_tag', 'to_tag', 'created_by']
    date_hierarchy = 'created_at'


@admin.register(TagTrending)
class TagTrendingAdmin(admin.ModelAdmin):
    list_display = [
        'tag', 'period', 'rank', 'usage_count',
        'growth_rate', 'trending_score', 'calculated_at'
    ]
    list_filter = ['period', 'calculated_at']
    search_fields = ['tag__name']
    raw_id_fields = ['tag']
    readonly_fields = [
        'usage_count', 'growth_rate', 'trending_score',
        'rank', 'calculated_at'
    ]
    ordering = ['period', 'rank']


@admin.register(TagAnalytics)
class TagAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'tag', 'total_usage', 'unique_authors',
        'avg_engagement', 'growth_rate_7d', 'growth_rate_30d',
        'quality_score', 'last_calculated'
    ]
    list_filter = ['last_calculated']
    search_fields = ['tag__name']
    readonly_fields = [
        'total_usage', 'unique_authors', 'avg_engagement',
        'first_used', 'last_used', 'peak_usage_date', 'peak_usage_count',
        'growth_rate_7d', 'growth_rate_30d', 'quality_score', 'last_calculated'
    ]
    
    def tag(self, obj):
        return obj.tag.name
    tag.admin_order_field = 'tag__name'


@admin.register(TagSubscription)
class TagSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'tag', 'notification_frequency',
        'is_active', 'created_at'
    ]
    list_filter = ['notification_frequency', 'is_active', 'created_at']
    search_fields = ['user__username', 'tag__name']
    raw_id_fields = ['tag', 'user']
    date_hierarchy = 'created_at'


@admin.register(TagSuggestion)
class TagSuggestionAdmin(admin.ModelAdmin):
    list_display = [
        'suggested_name', 'suggested_by', 'status',
        'ai_generated', 'ai_confidence', 'created_at'
    ]
    list_filter = ['status', 'ai_generated', 'created_at']
    search_fields = ['suggested_name', 'suggested_by__username']
    raw_id_fields = ['suggested_by', 'reviewed_by', 'created_tag']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    actions = ['approve_suggestions', 'reject_suggestions']
    
    def approve_suggestions(self, request, queryset):
        from apps.tags.services import TagService
        service = TagService()
        approved = 0
        
        for suggestion in queryset.filter(status='pending'):
            try:
                service.approve_tag_suggestion(suggestion, request.user)
                approved += 1
            except Exception as e:
                self.message_user(request, f'Failed to approve "{suggestion.suggested_name}": {e}', level='error')
        
        self.message_user(request, f'{approved} suggestions approved.')
    approve_suggestions.short_description = 'Approve selected suggestions'
    
    def reject_suggestions(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} suggestions rejected.')
    reject_suggestions.short_description = 'Reject selected suggestions'


@admin.register(TagBlacklist)
class TagBlacklistAdmin(admin.ModelAdmin):
    list_display = ['pattern', 'is_regex', 'is_active', 'reason', 'added_by', 'created_at']
    list_filter = ['is_regex', 'is_active', 'created_at']
    search_fields = ['pattern', 'reason']
    raw_id_fields = ['added_by']
    date_hierarchy = 'created_at'


@admin.register(TagMerge)
class TagMergeAdmin(admin.ModelAdmin):
    list_display = [
        'source_tag_name', 'target_tag', 'items_migrated',
        'merged_by', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['source_tag_name', 'target_tag__name']
    raw_id_fields = ['target_tag', 'merged_by']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'items_migrated']


class TagCollectionItemInline(admin.TabularInline):
    model = TagCollectionItem
    extra = 1
    raw_id_fields = ['tag']
    ordering = ['order']


@admin.register(TagCollection)
class TagCollectionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'owner', 'tag_count',
        'is_public', 'is_featured', 'follower_count', 'created_at'
    ]
    list_filter = ['is_public', 'is_featured', 'created_at']
    search_fields = ['name', 'description', 'owner__username']
    raw_id_fields = ['owner']
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    inlines = [TagCollectionItemInline]
    actions = ['mark_featured']
    
    def tag_count(self, obj):
        return obj.tags.count()
    tag_count.short_description = 'Tags'
    
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} collections marked as featured.')
    mark_featured.short_description = 'Mark as featured'


@admin.register(TagAlias)
class TagAliasAdmin(admin.ModelAdmin):
    list_display = [
        'alias', 'canonical_tag', 'redirect_count',
        'created_by', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['alias', 'canonical_tag__name']
    raw_id_fields = ['canonical_tag', 'created_by']
    readonly_fields = ['redirect_count', 'created_at']
    date_hierarchy = 'created_at'
