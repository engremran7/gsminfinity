"""
App Registry Service
====================

Business logic for managing app availability and feature flags.
This was moved from core (which should only contain infrastructure).
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class AppRegistryService:
    """
    Service for managing app registry and feature flags.
    
    Usage:
        service = AppRegistryService()
        if service.is_app_enabled('blog'):
            # Blog app is enabled
            pass
        
        enabled_apps = service.get_enabled_apps()
    """

    def is_app_enabled(self, app_label: str) -> bool:
        """
        Check if an app is enabled.
        
        Args:
            app_label: App identifier (e.g., 'blog', 'comments')
        
        Returns:
            True if app is enabled
        """
        try:
            from apps.app_registry.models import AppRegistry
            registry = AppRegistry.get_solo()
            field_name = f"{app_label}_enabled"
            return getattr(registry, field_name, True)  # Fail open
        except Exception as e:
            logger.error(f"Failed to check if {app_label} enabled: {e}")
            return True  # Fail open - don't break the app

    def get_enabled_apps(self) -> List[str]:
        """
        Get list of all enabled apps.
        
        Returns:
            List of app labels that are enabled
        """
        try:
            from apps.app_registry.models import AppRegistry
            registry = AppRegistry.get_solo()

            enabled = []
            for field in registry._meta.fields:
                if field.name.endswith('_enabled'):
                    if getattr(registry, field.name, False):
                        app_label = field.name.replace('_enabled', '')
                        enabled.append(app_label)

            return enabled
        except Exception as e:
            logger.error(f"Failed to get enabled apps: {e}")
            return []

    def get_disabled_apps(self) -> List[str]:
        """
        Get list of all disabled apps.
        
        Returns:
            List of app labels that are disabled
        """
        try:
            from apps.app_registry.models import AppRegistry
            registry = AppRegistry.get_solo()

            disabled = []
            for field in registry._meta.fields:
                if field.name.endswith('_enabled'):
                    if not getattr(registry, field.name, True):
                        app_label = field.name.replace('_enabled', '')
                        disabled.append(app_label)

            return disabled
        except Exception as e:
            logger.error(f"Failed to get disabled apps: {e}")
            return []

    def enable_app(self, app_label: str) -> bool:
        """
        Enable an app.
        
        Args:
            app_label: App identifier
        
        Returns:
            True if successful
        """
        try:
            from apps.app_registry.models import AppRegistry
            registry = AppRegistry.get_solo()
            field_name = f"{app_label}_enabled"

            if hasattr(registry, field_name):
                setattr(registry, field_name, True)
                registry.save()
                logger.info(f"Enabled app: {app_label}")
                return True
            else:
                logger.warning(f"No such app in registry: {app_label}")
                return False
        except Exception as e:
            logger.error(f"Failed to enable {app_label}: {e}")
            return False

    def disable_app(self, app_label: str) -> bool:
        """
        Disable an app.
        
        Args:
            app_label: App identifier
        
        Returns:
            True if successful
        """
        try:
            from apps.app_registry.models import AppRegistry
            registry = AppRegistry.get_solo()
            field_name = f"{app_label}_enabled"

            if hasattr(registry, field_name):
                setattr(registry, field_name, False)
                registry.save()
                logger.info(f"Disabled app: {app_label}")
                return True
            else:
                logger.warning(f"No such app in registry: {app_label}")
                return False
        except Exception as e:
            logger.error(f"Failed to disable {app_label}: {e}")
            return False

    def get_app_status(self) -> Dict[str, bool]:
        """
        Get status of all apps.
        
        Returns:
            Dictionary mapping app labels to enabled status
        """
        try:
            from apps.app_registry.models import AppRegistry
            registry = AppRegistry.get_solo()

            status = {}
            for field in registry._meta.fields:
                if field.name.endswith('_enabled'):
                    app_label = field.name.replace('_enabled', '')
                    status[app_label] = getattr(registry, field.name, False)

            return status
        except Exception as e:
            logger.error(f"Failed to get app status: {e}")
            return {}

    def bulk_enable(self, app_labels: List[str]) -> int:
        """
        Enable multiple apps.
        
        Args:
            app_labels: List of app identifiers
        
        Returns:
            Number of apps successfully enabled
        """
        count = 0
        for app_label in app_labels:
            if self.enable_app(app_label):
                count += 1
        return count

    def bulk_disable(self, app_labels: List[str]) -> int:
        """
        Disable multiple apps.
        
        Args:
            app_labels: List of app identifiers
        
        Returns:
            Number of apps successfully disabled
        """
        count = 0
        for app_label in app_labels:
            if self.disable_app(app_label):
                count += 1
        return count


__all__ = ['AppRegistryService']
