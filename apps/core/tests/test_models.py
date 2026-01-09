"""
Tests for core models.
"""
from django.test import TestCase
from apps.core.models import AppRegistry


class AppRegistryModelTest(TestCase):
    """Test cases for the AppRegistry singleton model."""

    def test_app_registry_singleton(self):
        """Test that AppRegistry is a singleton."""
        registry1 = AppRegistry.get_solo()
        registry2 = AppRegistry.get_solo()
        self.assertEqual(registry1.id, registry2.id)

    def test_app_registry_defaults(self):
        """Test default values for AppRegistry."""
        registry = AppRegistry.get_solo()
        # Test that we can access the object without errors
        self.assertIsNotNone(registry)
        self.assertIsInstance(registry, AppRegistry)
