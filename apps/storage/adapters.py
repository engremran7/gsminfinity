# Storage Adapters - Concrete implementations of storage interfaces
from typing import Dict, Any, Optional
from django.contrib.contenttypes.models import ContentType
from .interfaces import StorageProvider
from .services.orchestrator import UploadOrchestrator, DownloadOrchestrator


class GoogleDriveStorageAdapter(StorageProvider):
    """
    Google Drive implementation of StorageProvider interface
    Bridges firmware app with storage services
    """
    
    def __init__(self):
        self.upload_orchestrator = UploadOrchestrator()
        self.download_orchestrator = DownloadOrchestrator()
    
    def upload_file(
        self,
        local_path: str,
        firmware_object: Any,
        metadata: Dict[str, Any]
    ):
        """Upload firmware to Google Shared Drive"""
        from django.apps import apps
        
        # Get content type for GenericForeignKey
        Firmware = apps.get_model('firmware', 'Firmware')
        content_type = ContentType.objects.get_for_model(Firmware)
        
        # Extract metadata
        brand_name = metadata.get('brand_name', 'Unknown')
        
        # Use orchestrator to handle upload
        storage_location = self.upload_orchestrator.upload_firmware(
            local_path=local_path,
            firmware_object=firmware_object,
            content_type=content_type,
            brand_name=brand_name
        )
        
        return storage_location
    
    def initiate_download(self, user: Any, firmware_object: Any):
        """Initiate download for user"""
        from django.apps import apps
        
        # Get content type
        Firmware = apps.get_model('firmware', 'Firmware')
        content_type = ContentType.objects.get_for_model(Firmware)
        
        # Use orchestrator to handle download
        session = self.download_orchestrator.initiate_download(
            user=user,
            firmware_object=firmware_object,
            content_type=content_type
        )
        
        return session
    
    def get_download_status(self, session_id: str) -> Dict[str, Any]:
        """Get download session status"""
        from django.apps import apps
        
        UserDownloadSession = apps.get_model('storage', 'UserDownloadSession')
        
        try:
            session = UserDownloadSession.objects.get(id=session_id)
            return {
                'status': session.status,
                'download_url': session.download_url,
                'expires_at': session.expires_at,
                'time_remaining': session.time_remaining(),
                'is_expired': session.is_expired(),
            }
        except UserDownloadSession.DoesNotExist:
            return {
                'status': 'not_found',
                'error': 'Download session not found'
            }
    
    def add_external_link(
        self,
        firmware_object: Any,
        provider: str,
        url: str,
        metadata: Dict[str, Any] = None
    ):
        """Add external download link"""
        from django.apps import apps
        
        FirmwareStorageLocation = apps.get_model('storage', 'FirmwareStorageLocation')
        Firmware = apps.get_model('firmware', 'Firmware')
        
        content_type = ContentType.objects.get_for_model(Firmware)
        
        # Create storage location for external link
        storage_location = FirmwareStorageLocation.objects.create(
            content_type=content_type,
            object_id=firmware_object.id,
            storage_type='external_link',
            external_link_provider=provider,
            external_link_url=url,
            metadata=metadata or {}
        )
        
        return storage_location


# Registry for storage providers
_storage_providers = {}


def register_storage_provider(name: str, provider: StorageProvider):
    """Register a storage provider"""
    _storage_providers[name] = provider


def get_storage_provider(name: str = 'google_drive') -> Optional[StorageProvider]:
    """Get registered storage provider"""
    return _storage_providers.get(name)


# Auto-register Google Drive adapter
register_storage_provider('google_drive', GoogleDriveStorageAdapter())
