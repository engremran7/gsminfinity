from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import (
    FirmwareStorageLocation,
    SharedDriveAccount,
    UserDownloadSession,
)
from . import ServiceAccountRouter
from .gdrive import GoogleDriveService
from .placement import SmartPlacementAlgorithm

logger = logging.getLogger(__name__)


class DownloadOrchestrator:
    """
    Orchestrates firmware download flow:
    1. Check if firmware exists in shared drive
    2. Copy to user's GDrive with expirable link
    3. Fallback to external links if needed
    """

    def __init__(self):
        self.router = ServiceAccountRouter()
        self.link_ttl_hours = getattr(settings, "FIRMWARE_LINK_TTL_HOURS", 24)

    @transaction.atomic
    def initiate_download(
        self, user, firmware_object, content_type
    ) -> UserDownloadSession:
        """
        Main entry point for firmware download

        Args:
            user: Django User instance
            firmware_object: Firmware model instance (OfficialFirmware, etc.)
            content_type: ContentType of firmware

        Returns:
            UserDownloadSession
        """

        # Check for existing active session
        existing = UserDownloadSession.objects.filter(
            user=user,
            storage_location__content_type=content_type,
            storage_location__object_id=firmware_object.id,
            status__in=["pending", "copying", "ready"],
            expires_at__gt=timezone.now(),
        ).first()

        if existing:
            logger.info(
                f"Returning existing session {existing.id} for user {user.username}"
            )
            return existing

        # Try Google Drive first
        gdrive_location = (
            FirmwareStorageLocation.objects.filter(
                content_type=content_type,
                object_id=firmware_object.id,
                storage_type="shared_drive",
                is_primary=True,
            )
            .select_related("shared_drive")
            .first()
        )

        if gdrive_location and gdrive_location.is_available():
            return self._initiate_gdrive_download(user, gdrive_location)

        # Fallback to external links
        external_location = (
            FirmwareStorageLocation.objects.filter(
                content_type=content_type,
                object_id=firmware_object.id,
                storage_type="external_link",
            )
            .filter(
                models.Q(external_expiry__isnull=True)
                | models.Q(external_expiry__gt=timezone.now())
            )
            .order_by("-priority", "-created_at")
            .first()
        )

        if external_location:
            return self._create_external_download_session(user, external_location)

        # No download sources available
        raise ValueError("No download sources available for this firmware")

    def _initiate_gdrive_download(
        self, user, storage_location: FirmwareStorageLocation
    ) -> UserDownloadSession:
        """Copy firmware to user's GDrive and create download session"""

        # Get optimal service account
        file_size_gb = storage_location.file_size_gb()
        service_account = self.router.get_best_service_account(
            required_gb=file_size_gb,
            preferred_drive_id=str(storage_location.shared_drive.id)
            if storage_location.shared_drive
            else None,
        )

        if not service_account:
            logger.warning(
                f"All service accounts exhausted for {file_size_gb:.2f}GB transfer, "
                f"falling back to external links"
            )
            return self._fallback_to_external(user, storage_location)

        # Create download session
        session = UserDownloadSession.objects.create(
            user=user,
            storage_location=storage_location,
            service_account=service_account,
            status="pending",
            expires_at=timezone.now() + timezone.timedelta(hours=self.link_ttl_hours),
        )

        logger.info(
            f"Created download session {session.id} for {user.username} "
            f"using SA {service_account.name}"
        )

        # Trigger async copy task (will be implemented in tasks.py)
        from ..tasks import copy_firmware_to_user_drive

        copy_firmware_to_user_drive.delay(str(session.id))

        return session

    def _create_external_download_session(
        self, user, storage_location: FirmwareStorageLocation
    ) -> UserDownloadSession:
        """Create session for external link download"""

        session = UserDownloadSession.objects.create(
            user=user,
            storage_location=storage_location,
            user_gdrive_link=storage_location.external_url,
            status="ready",
            expires_at=storage_location.external_expiry
            or (timezone.now() + timezone.timedelta(days=30)),
        )

        logger.info(
            f"Created external download session {session.id} for {user.username} "
            f"using {storage_location.external_provider}"
        )

        return session

    def _fallback_to_external(self, user, gdrive_location: FirmwareStorageLocation):
        """Fallback when GDrive quota exhausted"""

        # Find external link for same firmware
        external_location = (
            FirmwareStorageLocation.objects.filter(
                content_type=gdrive_location.content_type,
                object_id=gdrive_location.object_id,
                storage_type="external_link",
            )
            .order_by("-priority", "-created_at")
            .first()
        )

        if external_location:
            return self._create_external_download_session(user, external_location)

        raise ValueError("All download sources exhausted (quota + no external links)")

    def cleanup_expired_sessions(self):
        """Delete expired files from user drives (called by periodic task)"""

        expired = UserDownloadSession.objects.filter(
            status="ready",
            expires_at__lt=timezone.now(),
            deleted_at__isnull=True,
            user_gdrive_file_id__isnull=False,
        )

        count = 0
        for session in expired:
            try:
                # Get service account to perform deletion
                sa = self.router.get_best_service_account(required_gb=0.1)

                if not sa:
                    logger.warning("No service accounts available for cleanup")
                    break

                gdrive_service = GoogleDriveService(sa)
                gdrive_service.delete_file(session.user_gdrive_file_id)

                session.status = "deleted"
                session.deleted_at = timezone.now()
                session.save(update_fields=["status", "deleted_at"])

                count += 1
                logger.info(f"Deleted expired file for session {session.id}")

            except Exception as e:
                logger.error(f"Failed to delete expired file {session.id}: {e}")

        logger.info(f"Cleaned up {count} expired download sessions")
        return count

    def get_session_status(self, session_id: str) -> dict:
        """Get detailed status of download session"""

        try:
            session = UserDownloadSession.objects.select_related(
                "storage_location", "service_account"
            ).get(id=session_id)

            return {
                "id": str(session.id),
                "status": session.status,
                "file_name": session.storage_location.file_name
                if session.storage_location
                else None,
                "file_size": session.storage_location.file_size_bytes
                if session.storage_location
                else None,
                "download_link": session.user_gdrive_link
                if session.status == "ready"
                else None,
                "expires_at": session.expires_at.isoformat(),
                "time_remaining": session.time_remaining().total_seconds(),
                "error_message": session.error_message
                if session.status == "failed"
                else None,
                "created_at": session.created_at.isoformat(),
                "copy_completed_at": session.copy_completed_at.isoformat()
                if session.copy_completed_at
                else None,
            }

        except UserDownloadSession.DoesNotExist:
            return {"error": "Session not found"}


class UploadOrchestrator:
    """
    Handles firmware uploads to shared drives with smart placement
    """

    def __init__(self):
        self.router = ServiceAccountRouter()
        self.placement = SmartPlacementAlgorithm()

    @transaction.atomic
    def upload_firmware(
        self,
        local_path: str,
        firmware_object,
        content_type,
        brand_name: str,
        model_name: str = None,
        variant_name: str = None,
        category: str = None,
        file_name: str = None,
    ) -> FirmwareStorageLocation:
        """
        Upload firmware to optimal shared drive

        Args:
            local_path: Path to local firmware file
            firmware_object: Firmware model instance
            content_type: ContentType of firmware
            brand_name: Brand name for organization
            model_name: Optional model name
            variant_name: Optional variant name
            category: Optional category
            file_name: Optional custom file name

        Returns:
            FirmwareStorageLocation
        """

        import os
        from pathlib import Path

        # Get file info
        file_path = Path(local_path)
        file_size = os.path.getsize(local_path)
        file_size_gb = file_size / (1024**3)

        if not file_name:
            file_name = file_path.name

        # Select optimal drive
        target_drive = self.placement.select_optimal_drive(
            brand_name=brand_name,
            model_name=model_name,
            variant_name=variant_name,
            category=category,
            file_count=1,
        )

        if not target_drive:
            raise ValueError("No available shared drives with capacity")

        # Get service account
        service_account = self.router.get_best_service_account(
            required_gb=file_size_gb, preferred_drive_id=str(target_drive.id)
        )

        if not service_account:
            raise ValueError(
                f"No service accounts available with {file_size_gb:.2f}GB quota"
            )

        # Get or create folder structure
        folder_org, _ = self.placement.get_or_create_folder_structure(
            target_drive, brand_name, model_name, variant_name, category
        )

        # Create folders in Google Drive if needed
        gdrive_service = GoogleDriveService(service_account)
        parent_folder_id = self._ensure_folder_structure(
            gdrive_service,
            target_drive,
            brand_name,
            model_name,
            variant_name,
            category,
            folder_org,
        )

        # Upload file
        upload_result = gdrive_service.upload_to_shared_drive(
            local_path=local_path, folder_id=parent_folder_id, file_name=file_name
        )

        # Record service account usage
        self.router.record_successful_operation(
            sa_id=str(service_account.id),
            bytes_transferred=file_size,
            speed_mbps=upload_result.get("speed_mbps"),
        )

        # Create storage location record
        storage_location = FirmwareStorageLocation.objects.create(
            content_type=content_type,
            object_id=firmware_object.id,
            storage_type="shared_drive",
            shared_drive=target_drive,
            gdrive_file_id=upload_result["file_id"],
            gdrive_folder_path=f"{brand_name}/{model_name or ''}/{variant_name or ''}/{category or ''}".strip(
                "/"
            ),
            file_name=file_name,
            file_size_bytes=file_size,
            md5_hash=upload_result.get("md5", ""),
            is_primary=True,
            is_verified=True,
            priority=100,
        )

        # Record file placement
        self.placement.record_file_placement(
            shared_drive=target_drive,
            brand_name=brand_name,
            file_size_bytes=file_size,
            model_name=model_name,
            variant_name=variant_name,
            category=category,
        )

        logger.info(
            f"Uploaded {file_name} ({file_size_gb:.2f}GB) to {target_drive.name} "
            f"using {service_account.name}"
        )

        return storage_location

    def _ensure_folder_structure(
        self,
        gdrive_service: GoogleDriveService,
        drive: SharedDriveAccount,
        brand_name: str,
        model_name: str = None,
        variant_name: str = None,
        category: str = None,
        folder_org: DriveFileOrganization = None,
    ) -> str:
        """
        Ensure folder hierarchy exists in Google Drive
        Returns the final folder ID where file should be uploaded
        """

        # Get or create brand folder
        if folder_org and folder_org.brand_folder_id:
            brand_folder_id = folder_org.brand_folder_id
        else:
            brand_folder_id = gdrive_service.create_folder(brand_name)
            if folder_org:
                folder_org.brand_folder_id = brand_folder_id
                folder_org.save(update_fields=["brand_folder_id"])

        parent_id = brand_folder_id

        # Create model folder if specified
        if model_name:
            if folder_org and folder_org.model_folder_id:
                model_folder_id = folder_org.model_folder_id
            else:
                model_folder_id = gdrive_service.create_folder(model_name, parent_id)
                if folder_org:
                    folder_org.model_folder_id = model_folder_id
                    folder_org.save(update_fields=["model_folder_id"])
            parent_id = model_folder_id

        # Create variant folder if specified
        if variant_name:
            if folder_org and folder_org.variant_folder_id:
                variant_folder_id = folder_org.variant_folder_id
            else:
                variant_folder_id = gdrive_service.create_folder(
                    variant_name, parent_id
                )
                if folder_org:
                    folder_org.variant_folder_id = variant_folder_id
                    folder_org.save(update_fields=["variant_folder_id"])
            parent_id = variant_folder_id

        # Create category folder if specified
        if category:
            if folder_org and folder_org.category_folder_id:
                category_folder_id = folder_org.category_folder_id
            else:
                category_folder_id = gdrive_service.create_folder(category, parent_id)
                if folder_org:
                    folder_org.category_folder_id = category_folder_id
                    folder_org.save(update_fields=["category_folder_id"])
            parent_id = category_folder_id

        return parent_id


# Import models for type hints
from django.db import models
