from __future__ import annotations

from unittest.mock import patch
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gsminfinity.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post, PostStatus
from apps.site_settings.models import SiteSettings
from .models import Comment

User = get_user_model()


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], ROOT_URLCONF="gsminfinity.urls", SECURE_SSL_REDIRECT=False)
class CommentModerationTests(TestCase):
    def setUp(self) -> None:
        ss = SiteSettings.get_solo()
        ss.enable_blog = True
        ss.enable_blog_comments = True
        ss.save()
        self.user = User.objects.create_user(email="u@example.com", password="pass")
        self.client = Client()
        self.client.force_login(self.user)
        self.post = Post.objects.create(
            title="Hello",
            body="Body",
            author=self.user,
            status=PostStatus.PUBLISHED,
            publish_at=timezone.now(),
        )

    @patch("apps.comments.views.ai_client.moderate_text")
    def test_add_comment_marks_spam_on_high_toxicity(self, mock_moderate):
        mock_moderate.return_value = {"label": "high", "toxicity_score": 0.9}
        url = reverse("comments:add_comment_json", kwargs={"slug": self.post.slug})
        res = self.client.post(url, {"body": "bad words"})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["status"], Comment.Status.SPAM)
        comment = Comment.objects.get(pk=payload["id"])
        self.assertEqual(comment.status, Comment.Status.SPAM)
        self.assertFalse(comment.is_approved)

    def test_list_comments_excludes_non_approved(self):
        approved = Comment.objects.create(
            post=self.post,
            user=self.user,
            body="ok",
            status=Comment.Status.APPROVED,
            is_approved=True,
        )
        Comment.objects.create(
            post=self.post,
            user=self.user,
            body="nope",
            status=Comment.Status.SPAM,
            is_approved=False,
        )
        url = reverse("comments:list_comments", kwargs={"slug": self.post.slug})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        ids = [c["id"] for c in res.json()["items"]]
        self.assertIn(approved.id, ids)
        self.assertEqual(len(ids), 1)

    def test_moderation_actions(self):
        staff = User.objects.create_user(email="staff@example.com", password="pass", is_staff=True)
        self.client.force_login(staff)
        comment = Comment.objects.create(
            post=self.post,
            user=self.user,
            body="pending",
            status=Comment.Status.PENDING,
            is_approved=False,
        )
        url = reverse("comments:moderation_action")
        res = self.client.post(url, {"comment_id": comment.id, "action": "approve"})
        self.assertEqual(res.status_code, 302)
        comment.refresh_from_db()
        self.assertEqual(comment.status, Comment.Status.APPROVED)
        self.assertTrue(comment.is_approved)
