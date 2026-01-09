# Firmware-Storage Bridge - Helper utilities for firmware app
from typing import Any

from django.apps import apps


class FirmwareStorageHelper:
    """
    Helper class for firmware app to interact with storage
    Uses signals and adapters for loose coupling
    """

    @staticmethod
    def upload_firmware(
        firmware_object: Any,
        local_path: str,
        brand_name: str,
        model_name: str | None = None,
        variant_name: str | None = None,
        category: str = "firmware",
    ):
        """
        Upload firmware file to cloud storage

        Usage in firmware app:
            from apps.storage.helpers import FirmwareStorageHelper

            location = FirmwareStorageHelper.upload_firmware(
                firmware_object=firmware,
                local_path="/tmp/firmware.zip",
                brand_name="Samsung",
                model_name="Galaxy S21",
                variant_name="SM-G991B"
            )

        Args:
            firmware_object: Firmware model instance
            local_path: Path to local file
            brand_name: Brand name for organization
            model_name: Optional model name
            variant_name: Optional variant name
            category: File category (firmware, tools, guides)

        Returns:
            FirmwareStorageLocation instance or None if storage app not installed
        """
        # Check if storage app is installed
        if not apps.is_installed("apps.storage"):
            return None

        # Emit signal for upload request
        from apps.core.signals import firmware_upload_requested

        firmware_upload_requested.send(
            sender=firmware_object.__class__,
            firmware=firmware_object,
            local_path=local_path,
            metadata={
                "brand_name": brand_name,
                "model_name": model_name,
                "variant_name": variant_name,
                "category": category,
            },
        )

        # Use adapter for direct upload (if needed immediately)
        try:
            from .adapters import get_storage_provider

            provider = get_storage_provider("google_drive")
            if provider:
                return provider.upload_file(
                    local_path=local_path,
                    firmware_object=firmware_object,
                    metadata={
                        "brand_name": brand_name,
                        "model_name": model_name,
                        "variant_name": variant_name,
                        "category": category,
                    },
                )
        except Exception as e:
            print(f"Storage upload error: {e}")
            return None

    @staticmethod
    def request_download(user: Any, firmware_object: Any):
        """
        Request firmware download for user

        Usage in firmware views:
            from apps.storage.helpers import FirmwareStorageHelper

            session = FirmwareStorageHelper.request_download(
                user=request.user,
                firmware_object=firmware
            )

            if session:
                return JsonResponse({
                    'session_id': str(session.id),
                    'status': session.status
                })

        Args:
            user: Django User instance
            firmware_object: Firmware model instance

        Returns:
            UserDownloadSession instance or None
        """
        # Check if storage app is installed
        if not apps.is_installed("apps.storage"):
            return None

        # Emit signal for download request
        from apps.core.signals import firmware_download_requested

        firmware_download_requested.send(
            sender=firmware_object.__class__, user=user, firmware=firmware_object
        )

        # Use adapter for download
        try:
            from .adapters import get_storage_provider

            provider = get_storage_provider("google_drive")
            if provider:
                return provider.initiate_download(
                    user=user, firmware_object=firmware_object
                )
        except Exception as e:
            print(f"Storage download error: {e}")
            return None

    @staticmethod
    def get_download_status(session_id: str) -> dict[str, Any]:
        """
        Get download session status

        Usage in firmware views:
            status = FirmwareStorageHelper.get_download_status(session_id)
            if status['status'] == 'ready':
                return redirect(status['download_url'])

        Args:
            session_id: UUID of download session

        Returns:
            Dict with status, url, expires_at, etc.
        """
        if not apps.is_installed("apps.storage"):
            return {"status": "not_available", "error": "Storage app not installed"}

        try:
            from .adapters import get_storage_provider

            provider = get_storage_provider("google_drive")
            if provider:
                return provider.get_download_status(session_id)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def add_external_link(
        firmware_object: Any,
        provider: str,
        url: str,
        password: str | None = None,
        notes: str | None = None,
    ):
        """
        Add external download link (MediaFire, MEGA, etc.)

        Usage in firmware admin:
            FirmwareStorageHelper.add_external_link(
                firmware_object=firmware,
                provider='mediafire',
                url='https://mediafire.com/file/xyz',
                password='optional_password'
            )

        Args:
            firmware_object: Firmware model instance
            provider: Provider name (mediafire, mega, google_drive, dropbox)
            url: Download URL
            password: Optional password
            notes: Optional notes

        Returns:
            FirmwareStorageLocation instance or None
        """
        if not apps.is_installed("apps.storage"):
            return None

        try:
            from .adapters import get_storage_provider

            storage_provider = get_storage_provider("google_drive")
            if storage_provider:
                metadata = {}
                if password:
                    metadata["password"] = password
                if notes:
                    metadata["notes"] = notes

                return storage_provider.add_external_link(
                    firmware_object=firmware_object,
                    provider=provider,
                    url=url,
                    metadata=metadata,
                )
        except Exception as e:
            print(f"External link error: {e}")
            return None

    @staticmethod
    def get_storage_locations(firmware_object: Any) -> list:
        """
        Get all storage locations for firmware

        Returns:
            List of FirmwareStorageLocation instances
        """
        if not apps.is_installed("apps.storage"):
            return []

        try:
            FirmwareStorageLocation = apps.get_model(
                "storage", "FirmwareStorageLocation"
            )
            from django.contrib.contenttypes.models import ContentType

            Firmware = apps.get_model("firmware", "Firmware")
            content_type = ContentType.objects.get_for_model(Firmware)

            return FirmwareStorageLocation.objects.filter(
                content_type=content_type, object_id=firmware_object.id, is_active=True
            ).order_by("-created_at")
        except Exception as e:
            print(f"Get locations error: {e}")
            return []

    @staticmethod
    def check_storage_quota() -> dict[str, Any]:
        """
        Check available storage quota across drives

        Returns:
            Dict with quota information per drive
        """
        if not apps.is_installed("apps.storage"):
            return {"available": False}

        try:
            SharedDriveAccount = apps.get_model("storage", "SharedDriveAccount")

            drives = SharedDriveAccount.objects.filter(is_active=True)
            quota_info = {"available": True, "drives": []}

            for drive in drives:
                quota_info["drives"].append(
                    {
                        "drive_id": drive.drive_id,
                        "name": drive.drive_name,
                        "files": drive.file_count,
                        "capacity": drive.total_capacity,
                        "utilization": drive.utilization_percent(),
                        "health": drive.health_status,
                    }
                )

            return quota_info
        except Exception as e:
            return {"available": False, "error": str(e)}
