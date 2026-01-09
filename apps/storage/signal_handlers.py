# Storage App - Signal Handler for Firmware Download Ready
import logging

from django.dispatch import receiver

from apps.core.signals import firmware_download_ready

logger = logging.getLogger(__name__)


@receiver(firmware_download_ready)
def send_download_ready_notification(sender, session, user, file_name, expires_at, **kwargs):
    """
    Send notification when firmware download is ready
    Uses core notification service (loose coupling)
    """
    try:
        from apps.core.services.notifications import DjangoNotificationService

        notif_service = DjangoNotificationService()

        # Calculate remaining hours
        from django.utils import timezone
        remaining = expires_at - timezone.now()
        remaining_hours = int(remaining.total_seconds() / 3600)

        notif_service.send_notification(
            user=user,
            notification_type='firmware_ready',
            title='Firmware Ready for Download',
            message=f'{file_name} is ready. Download link expires in {remaining_hours} hours.',
            link=f'/api/storage/download/link/{session.id}/'
        )

        logger.info(f"Sent download ready notification to {user.username}")

    except Exception as e:
        logger.error(f"Failed to send download ready notification: {e}")


@receiver(firmware_download_ready)
def log_download_analytics(sender, session, user, file_name, **kwargs):
    """
    Log download analytics for reporting
    """
    try:
        logger.info(
            f"Download ready: user={user.username}, "
            f"file={file_name}, session={session.id}"
        )
        # Add more analytics logging here if needed
    except Exception as e:
        logger.error(f"Failed to log download analytics: {e}")
