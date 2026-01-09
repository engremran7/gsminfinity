"""
Core Services Package
Provides service implementations for cross-app communication.
"""

from .notifications import notification_service
from .settings import settings_provider

__all__ = ["settings_provider", "notification_service"]
