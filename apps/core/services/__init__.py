"""
Core Services Package
Provides service implementations for cross-app communication.
"""
from .settings import settings_provider
from .notifications import notification_service

__all__ = ['settings_provider', 'notification_service']
