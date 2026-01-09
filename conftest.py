"""
Pytest configuration for GsmInfinity Django project.

This module configures pytest-django for database access and provides
common fixtures for testing.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import django
import pytest

if TYPE_CHECKING:
    pass


def pytest_configure():
    """Configure Django settings before pytest runs."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings_dev")
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-testing-only")
    os.environ.setdefault("DB_ENGINE", "django.db.backends.postgresql")

    # Ensure Django is setup before tests run
    django.setup()


# ============================================================
# Database Fixtures
# ============================================================

@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """
    Set up the test database.
    
    This fixture runs once per test session and ensures the database
    is properly configured with all migrations applied.
    """
    from django.core.management import call_command

    with django_db_blocker.unblock():
        # Ensure migrations are applied to test database
        call_command("migrate", "--run-syncdb", verbosity=0)


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    # Use a unique username for each test to avoid conflicts
    import uuid

    from apps.users.models import CustomUser
    unique_id = uuid.uuid4().hex[:8]

    user = CustomUser.objects.create_user(
        username=f"testadmin_{unique_id}",
        email=f"testadmin_{unique_id}@test.local",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user for testing."""
    # Use a unique username for each test to avoid conflicts
    import uuid

    from apps.users.models import CustomUser
    unique_id = uuid.uuid4().hex[:8]

    user = CustomUser.objects.create_user(
        username=f"testuser_{unique_id}",
        email=f"testuser_{unique_id}@test.local",
        password="testpass123",
        is_staff=False,
        is_superuser=False,
        is_active=True,
    )
    return user


@pytest.fixture
def authenticated_client(client, regular_user):
    """Return a Django test client with an authenticated regular user."""
    client.force_login(regular_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Return a Django test client with an authenticated admin user."""
    client.force_login(admin_user)
    return client
