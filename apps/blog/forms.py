from __future__ import annotations

from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = [
            "title",
            "summary",
            "body",
            "category",
            "tags",
            "status",
            "publish_at",
            "featured",
            "seo_title",
            "seo_description",
            "canonical_url",
            "hero_image",
        ]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 8, "class": "form-control"}),
            "summary": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "publish_at": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "form-control"}
            ),
            "seo_description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }
