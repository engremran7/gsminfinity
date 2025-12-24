# Storage App - Multi-cloud storage management for firmware files
"""
Cloud Storage Management System
================================

Architecture:
- 3 Google Shared Drives @ 400k file limit each
- 300 Service Accounts (100 per drive) @ 750GB/day quota
- Smart placement algorithm with hierarchical organization
- Intelligent SA rotation based on quota/speed/freshness/reliability
- Temporary user downloads with 24h expirable links
- Signal-based loose coupling with other apps

Usage:
    # Check if storage is available
    from django.apps import apps
    if apps.is_installed('apps.storage'):
        from apps.storage.helpers import FirmwareStorageHelper
        
        # Upload firmware
        location = FirmwareStorageHelper.upload_firmware(
            firmware_object=firmware,
            local_path="/path/to/file.zip",
            brand_name="Samsung"
        )
        
        # Request download
        session = FirmwareStorageHelper.request_download(
            user=request.user,
            firmware_object=firmware
        )

For complete integration examples, see:
    apps/storage/INTEGRATION_EXAMPLES.py
"""

# Public API exports
__all__ = [
    'FirmwareStorageHelper',
    'StorageProvider',
    'GoogleDriveStorageAdapter',
]

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name == 'FirmwareStorageHelper':
        from .helpers import FirmwareStorageHelper
        return FirmwareStorageHelper
    elif name == 'StorageProvider':
        from .interfaces import StorageProvider
        return StorageProvider
    elif name == 'GoogleDriveStorageAdapter':
        from .adapters import GoogleDriveStorageAdapter
        return GoogleDriveStorageAdapter
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
