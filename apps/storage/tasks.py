from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=300,   # 5 minutes for file copy
    time_limit=600,        # 10 minutes hard limit
)
def copy_firmware_to_user_drive(self, session_id: str):
    """
    Async task to copy firmware from shared drive to user's personal drive
    Uses lazy imports for modularity
    
    Args:
        session_id: UUID of UserDownloadSession
    """
    try:
        # Lazy imports to avoid circular dependencies
        UserDownloadSession = apps.get_model('storage', 'UserDownloadSession')
        from .services.gdrive import GoogleDriveService
        from .services import ServiceAccountRouter
        
        session = UserDownloadSession.objects.select_related(
            'storage_location__shared_drive',
            'service_account',
            'user'
        ).get(id=session_id)
        
        session.status = 'copying'
        session.save(update_fields=['status'])
        
        # Get GDrive service
        gdrive_service = GoogleDriveService(session.service_account)
        
        # Copy file to user's drive
        result = gdrive_service.copy_to_user_drive(
            source_file_id=session.storage_location.gdrive_file_id,
            user_email=session.user.email,
            file_name=session.storage_location.file_name
        )
        
        # Update session with results
        session.user_gdrive_file_id = result['file_id']
        session.user_gdrive_link = result['download_link']
        session.copy_completed_at = timezone.now()
        session.status = 'ready'
        session.save()
        
        # Record service account usage with transaction safety
        with transaction.atomic():
            router = ServiceAccountRouter()
            router.record_successful_operation(
                sa_id=str(session.service_account.id),
                bytes_transferred=session.storage_location.file_size_bytes
            )
            
            # Increment download count atomically (prevents race conditions)
            from django.db.models import F
            session.storage_location.__class__.objects.filter(
                id=session.storage_location.id
            ).update(download_count=F('download_count') + 1)
            
            # Refresh from DB to get updated count
            session.storage_location.refresh_from_db()
        
        # Send signal instead of direct notification (loose coupling)
        try:
            from apps.core.signals import firmware_download_ready
            firmware_download_ready.send(
                sender=session.__class__,
                session=session,
                user=session.user,
                file_name=session.storage_location.file_name,
                expires_at=session.expires_at
            )
        except Exception as e:
            logger.warning(f"Failed to send signal: {e}")
        
        logger.info(f"Successfully copied firmware for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to copy firmware for session {session_id}: {e}")
        
        try:
            UserDownloadSession = apps.get_model('storage', 'UserDownloadSession')
            ServiceAccount = apps.get_model('storage', 'ServiceAccount')
            
            session = UserDownloadSession.objects.select_related('service_account').get(id=session_id)
            
            # Mark session as failed
            session.status = 'failed'
            session.error_message = str(e)[:500]  # Truncate long errors
            session.save(update_fields=['status', 'error_message'])
            
            # Mark service account failure (but don't deduct quota - it wasn't used)
            if session.service_account:
                with transaction.atomic():
                    sa = ServiceAccount.objects.select_for_update().get(id=session.service_account.id)
                    sa.consecutive_failures = (sa.consecutive_failures or 0) + 1
                    
                    # Disable if too many failures
                    if sa.consecutive_failures >= 5:
                        sa.is_active = False
                        logger.error(f"Service account {sa.name} disabled after 5 failures")
                    
                    sa.save(update_fields=['consecutive_failures', 'is_active'])
        except Exception as inner_e:
            logger.error(f"Failed to handle error for session {session_id}: {inner_e}")
        
        # Retry with different service account
        if self.request.retries < self.max_retries:
            # Exponential backoff: 60s, 120s, 240s
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=e, countdown=countdown)


@shared_task(
    bind=True,
    acks_late=True,
    soft_time_limit=120,
    time_limit=180,
)
def cleanup_expired_download_sessions(self):
    """
    Periodic task (runs every hour) to delete expired user drive files
    """
    from .services.orchestrator import DownloadOrchestrator
    
    orchestrator = DownloadOrchestrator()
    count = orchestrator.cleanup_expired_sessions()
    logger.info(f"Cleanup task completed: {count} expired sessions deleted")
    return count


@shared_task(
    bind=True,
    acks_late=True,
    soft_time_limit=300,   # 5 minutes - iterates over multiple accounts
    time_limit=600,
)
def health_check_service_accounts(self):
    """
    Periodic task (runs every 30 minutes) to check service account health.
    Uses .iterator() for memory efficiency with large account sets.
    """
    ServiceAccount = apps.get_model('storage', 'ServiceAccount')
    from .services.gdrive import GoogleDriveService
    
    # Use iterator with batch limit for memory efficiency
    accounts = ServiceAccount.objects.filter(is_active=True)[:100]
    
    healthy_count = 0
    unhealthy_count = 0
    
    for sa in accounts.iterator(chunk_size=20):
        try:
            gdrive_service = GoogleDriveService(sa)
            # Simple API call to verify account is working
            gdrive_service.service.about().get(fields='storageQuota').execute()
            
            # Reset failure counter on success
            sa.consecutive_failures = 0
            sa.last_used_at = timezone.now()
            sa.save(update_fields=['consecutive_failures', 'last_used_at'])
            
            healthy_count += 1
            
        except Exception as e:
            logger.warning(f"Service account {sa.name} health check failed: {e}")
            sa.consecutive_failures += 1
            
            if sa.consecutive_failures >= 5:
                sa.is_active = False
                logger.error(f"Service account {sa.name} disabled after 5 consecutive failures")
            
            sa.save(update_fields=['consecutive_failures', 'is_active'])
            unhealthy_count += 1
    
    logger.info(
        f"Health check completed: {healthy_count} healthy, {unhealthy_count} unhealthy"
    )
    
    return {'healthy': healthy_count, 'unhealthy': unhealthy_count}


@shared_task
def update_shared_drive_health():
    """
    Periodic task (runs every 15 minutes) to update shared drive health status
    """
    SharedDriveAccount = apps.get_model('storage', 'SharedDriveAccount')
    drives = SharedDriveAccount.objects.filter(is_active=True)
    
    for drive in drives:
        drive.update_health_status()
    
    logger.info(f"Updated health status for {drives.count()} shared drives")
    return drives.count()


@shared_task
def generate_quota_analytics():
    """
    Daily task to generate quota usage analytics
    """
    ServiceAccount = apps.get_model('storage', 'ServiceAccount')
    ServiceAccountQuotaLog = apps.get_model('storage', 'ServiceAccountQuotaLog')
    
    today = timezone.now().date()
    
    created_count = 0
    for sa in ServiceAccount.objects.all():
        _, created = ServiceAccountQuotaLog.objects.update_or_create(
            service_account=sa,
            date=today,
            defaults={
                'total_bytes_transferred': sa.total_bytes_transferred,
                'total_operations': sa.total_operations
            }
        )
        if created:
            created_count += 1
    
    logger.info(f"Generated {created_count} new quota log entries for {today}")
    return created_count


@shared_task
def verify_storage_integrity():
    """
    Daily task to verify random sample of stored files
    """
    from .models import FirmwareStorageLocation
    import random
    
    # Get random sample of 10 files
    all_files = list(FirmwareStorageLocation.objects.filter(
        storage_type='shared_drive',
        is_verified=True
    ).values_list('id', flat=True))
    
    if not all_files:
        return 0
    
    sample_size = min(10, len(all_files))
    sample_ids = random.sample(all_files, sample_size)
    
    verified_count = 0
    failed_count = 0
    
    for file_id in sample_ids:
        try:
            storage_loc = FirmwareStorageLocation.objects.select_related(
                'shared_drive'
            ).get(id=file_id)
            
            # Get service account for this drive
            router = ServiceAccountRouter()
            sa = router.get_best_service_account(
                required_gb=0.1,
                preferred_drive_id=str(storage_loc.shared_drive.id) if storage_loc.shared_drive else None
            )
            
            if not sa:
                continue
            
            gdrive_service = GoogleDriveService(sa)
            
            # Verify file exists and MD5 matches
            is_valid = gdrive_service.verify_file_integrity(
                file_id=storage_loc.gdrive_file_id,
                expected_md5=storage_loc.md5_hash
            )
            
            if is_valid:
                storage_loc.last_verified_at = timezone.now()
                storage_loc.consecutive_failures = 0
                storage_loc.save(update_fields=['last_verified_at', 'consecutive_failures'])
                verified_count += 1
            else:
                storage_loc.consecutive_failures += 1
                storage_loc.save(update_fields=['consecutive_failures'])
                failed_count += 1
                
        except Exception as e:
            logger.error(f"Integrity check failed for {file_id}: {e}")
            failed_count += 1
    
    logger.info(
        f"Integrity check completed: {verified_count} verified, {failed_count} failed"
    )
    
    return {'verified': verified_count, 'failed': failed_count}


@shared_task
def cleanup_failed_sessions():
    """
    Daily task to cleanup failed download sessions older than 7 days
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=7)
    
    deleted_count = UserDownloadSession.objects.filter(
        status='failed',
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} failed sessions older than 7 days")
    return deleted_count


@shared_task
def balance_drive_report():
    """
    Weekly task to generate drive balance report
    """
    from .services.placement import SmartPlacementAlgorithm
    
    placement = SmartPlacementAlgorithm()
    analysis = placement.balance_drives()
    
    if analysis['needs_rebalancing']:
        logger.warning(
            f"Drive rebalancing needed! Recommendations: {analysis['recommendations']}"
        )
        
        # Send notification to admins
        try:
            from apps.core.services.notifications import DjangoNotificationService
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            admins = User.objects.filter(is_staff=True, is_active=True)
            
            notif_service = DjangoNotificationService()
            
            for admin in admins:
                notif_service.send_notification(
                    user=admin,
                    notification_type='system_alert',
                    title='Shared Drive Rebalancing Needed',
                    message=f"Drive utilization imbalance detected. {len(analysis['recommendations'])} recommendations available.",
                    link='/admin/storage/shareddriveaccount/'
                )
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
    
    return analysis
