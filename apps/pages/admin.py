from django.contrib import admin

from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "status",
        "access_level",
        "include_in_sitemap",
        "last_modified",
    )
    list_filter = ("status", "access_level", "include_in_sitemap", "changefreq")
    search_fields = ("title", "slug", "seo_title")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "last_modified")
    fieldsets = (
        (
            "Content",
            {
                "fields": (
                    "title",
                    "slug",
                    "content",
                    "content_format",
                    "status",
                    "access_level",
                )
            },
        ),
        ("Publishing", {"fields": ("publish_at", "unpublish_at")}),
        (
            "SEO",
            {"fields": ("seo_title", "seo_description", "og_image", "canonical_url")},
        ),
        (
            "Sitemap",
            {
                "fields": (
                    "include_in_sitemap",
                    "changefreq",
                    "priority",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_modified")}),
    )
