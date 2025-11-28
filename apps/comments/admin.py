from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "status", "toxicity_score", "is_deleted", "created_at")
    list_filter = ("status", "is_deleted", "created_at")
    search_fields = ("body", "user__email", "post__title")
    raw_id_fields = ("post", "user")
    actions = ("mark_approved", "mark_rejected", "mark_spam", "soft_delete")

    @admin.action(description="Mark selected comments approved")
    def mark_approved(self, request, queryset):
        queryset.update(status="approved", is_approved=True)

    @admin.action(description="Mark selected comments rejected")
    def mark_rejected(self, request, queryset):
        queryset.update(status="rejected", is_approved=False)

    @admin.action(description="Mark selected comments spam")
    def mark_spam(self, request, queryset):
        queryset.update(status="spam", is_approved=False)

    @admin.action(description="Soft delete selected comments")
    def soft_delete(self, request, queryset):
        queryset.update(is_deleted=True)
