# Storage App Signal Handlers
import logging

from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='storage.FirmwareStorageLocation')
def on_firmware_uploaded(sender, instance, created, **kwargs):
    """
    Signal handler when firmware is uploaded to storage
    Sends firmware_uploaded signal to notify other apps
    """
    if created and instance.storage_type == 'shared_drive':
        try:
            from apps.core.signals import firmware_uploaded
            firmware_uploaded.send(
                sender=sender,
                firmware_object=None,  # Will be populated by firmware app
                storage_location=instance
            )
            logger.info(f"Firmware uploaded signal sent for {instance.file_name}")
        except Exception as e:
            logger.error(f"Failed to send firmware_uploaded signal: {e}")


@receiver(pre_delete, sender='storage.FirmwareStorageLocation')
def cleanup_gdrive_file_on_delete(sender, instance, **kwargs):
    """
    Delete file from Google Drive when storage location is deleted
    """
    if instance.storage_type == 'shared_drive' and instance.gdrive_file_id:
        try:
            from .services import ServiceAccountRouter
            from .services.gdrive import GoogleDriveService

            router = ServiceAccountRouter()
            sa = router.get_best_service_account(
                required_gb=0.1,
                preferred_drive_id=str(instance.shared_drive.id) if instance.shared_drive else None
            )

            if sa:
                gdrive_service = GoogleDriveService(sa)
                gdrive_service.delete_file(instance.gdrive_file_id)
                logger.info(f"Deleted file {instance.gdrive_file_id} from Google Drive")
        except Exception as e:
            logger.error(f"Failed to delete file from Google Drive: {e}")


@receiver(post_delete, sender='storage.FirmwareStorageLocation')
def update_drive_counters_on_delete(sender, instance, **kwargs):
    """
    Update shared drive file counters when storage location is deleted
    """
    if instance.storage_type == 'shared_drive' and instance.shared_drive:
        try:
            from .services.placement import SmartPlacementAlgorithm
            placement = SmartPlacementAlgorithm()
            placement.record_file_deletion(instance)
        except Exception as e:
            logger.error(f"Failed to update drive counters: {e}")


@receiver(post_save, sender='storage.SharedDriveAccount')
def check_drive_capacity_on_update(sender, instance, **kwargs):
    """
    Check if drive is approaching capacity and send alert signal
    """
    utilization = instance.utilization_percent()

    # Send alert if utilization exceeds 90%
    if utilization >= 90 and instance.is_active:
        try:
            from apps.core.signals import storage_quota_exhausted
            storage_quota_exhausted.send(
                sender=sender,
                shared_drive=instance,
                utilization_percent=utilization
            )
            logger.warning(
                f"Drive {instance.name} quota exhausted signal sent "
                f"({utilization:.1f}% utilization)"
            )
        except Exception as e:
            logger.error(f"Failed to send quota exhausted signal: {e}")

    # Send critical health alert
    if instance.health_status in ['critical', 'full']:
        try:
            from apps.core.signals import storage_health_critical
            storage_health_critical.send(
                sender=sender,
                shared_drive=instance,
                issue=instance.health_status
            )
            logger.error(
                f"Drive {instance.name} health critical: {instance.health_status}"
            )
        except Exception as e:
            logger.error(f"Failed to send health critical signal: {e}")

