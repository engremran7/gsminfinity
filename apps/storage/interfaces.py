# Storage Interfaces - Abstract interfaces for loose coupling
from abc import ABC, abstractmethod
from typing import Any, Dict


class StorageProvider(ABC):
    """
    Abstract interface for cloud storage operations
    Allows firmware app to use storage without direct dependency
    """

    @abstractmethod
    def upload_file(
        self,
        local_path: str,
        firmware_object: Any,
        metadata: Dict[str, Any]
    ) -> 'StorageLocation':
        """
        Upload firmware file to cloud storage
        
        Args:
            local_path: Path to local file
            firmware_object: Firmware model instance
            metadata: Dict with brand_name, model_name, variant_name, category
            
        Returns:
            StorageLocation object with file details
        """
        pass

    @abstractmethod
    def initiate_download(
        self,
        user: Any,
        firmware_object: Any
    ) -> 'DownloadSession':
        """
        Initiate firmware download for user
        
        Args:
            user: Django User instance
            firmware_object: Firmware model instance
            
        Returns:
            DownloadSession with status and link
        """
        pass

    @abstractmethod
    def get_download_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get download session status
        
        Args:
            session_id: UUID of download session
            
        Returns:
            Dict with status, link, expires_at, etc.
        """
        pass

    @abstractmethod
    def add_external_link(
        self,
        firmware_object: Any,
        provider: str,
        url: str,
        metadata: Dict[str, Any] = None
    ) -> 'StorageLocation':
        """
        Add external download link (MediaFire, MEGA, etc.)
        
        Args:
            firmware_object: Firmware model instance
            provider: Provider name (mediafire, mega, etc.)
            url: Download URL
            metadata: Optional metadata (password, expiry, etc.)
            
        Returns:
            StorageLocation for external link
        """
        pass
