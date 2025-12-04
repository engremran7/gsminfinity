
from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import BlogSettings, Category, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_published", "published_at")
    list_filter = ("is_published", "category")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    raw_id_fields = ("author",)
    date_hierarchy = "published_at"


@admin.register(BlogSettings)
class BlogSettingsAdmin(SingletonModelAdmin):
    list_display = ("enable_blog", "enable_blog_comments", "allow_user_blog_posts")
    fieldsets = (
        (None, {"fields": ("enable_blog", "enable_blog_comments")}),
        ("User posting", {"fields": ("allow_user_blog_posts",)}),
    )

    def has_add_permission(self, request):
        return False


