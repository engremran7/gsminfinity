"""
Tests for blog models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.blog.models import Post, Category, PostStatus

User = get_user_model()


class PostModelTest(TestCase):
    """Test cases for the Post model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )

    def test_post_creation(self):
        """Test creating a post."""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            category=self.category,
            status=PostStatus.DRAFT,
            body='Test content'
        )
        self.assertEqual(post.title, 'Test Post')
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.category, self.category)
        self.assertEqual(post.status, PostStatus.DRAFT)

    def test_post_str(self):
        """Test the string representation of a post."""
        post = Post.objects.create(
            title='Test Post',
            slug='test-post',
            author=self.user,
            category=self.category,
            status=PostStatus.DRAFT,
            body='Test content'
        )
        self.assertEqual(str(post), 'Test Post')


class CategoryModelTest(TestCase):
    """Test cases for the Category model."""

    def test_category_creation(self):
        """Test creating a category."""
        category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.assertEqual(category.name, 'Test Category')
        self.assertEqual(category.slug, 'test-category')

    def test_category_str(self):
        """Test the string representation of a category."""
        category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.assertEqual(str(category), 'Test Category')
