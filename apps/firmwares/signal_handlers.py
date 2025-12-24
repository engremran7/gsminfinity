# Signal handlers for firmware tracking and storage integration
"""
Handles:
- Firmware upload tracking
- Download tracking and completion
- Integration with storage app
- Cache invalidation
- Analytics updates

All handlers use async tasks where possible to avoid blocking requests
"""

from django.apps import apps
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import logging

logger = logging.getLogger(__name__)

# Import autofill system
try:
    from apps.firmwares.admin_autofill import FirmwareAutoFill
except ImportError:
    FirmwareAutoFill = None


# === STORAGE INTEGRATION SIGNALS ===

try:
    from apps.core.signals import (
        firmware_uploaded,
        firmware_download_requested,
        firmware_download_ready,
        storage_quota_exhausted,
    )
    
    @receiver(firmware_uploaded)
    def handle_firmware_uploaded(sender, storage_location, firmware, **kwargs):
        """
        When firmware uploaded to storage:
        1. Update firmware model status
        2. Invalidate caches
        3. Log to analytics
        """
        try:
            # Update firmware model (if it has storage-related fields)
            if hasattr(firmware, 'is_uploaded'):
                firmware.is_uploaded = True
                firmware.save(update_fields=['is_uploaded'])
            
            # Invalidate homepage cache
            from apps.pages.widgets import HomePageWidgetService
            HomePageWidgetService.invalidate_caches(['latest_firmwares'])
            
            logger.info(f"Firmware uploaded: {firmware.id} via storage app")
            
        except Exception as e:
            logger.error(f"Error handling firmware_uploaded signal: {e}")
    
    @receiver(firmware_download_requested)
    def handle_download_requested(sender, user, firmware, **kwargs):
        """
        When user requests firmware download:
        1. Log download attempt
        2. Track for analytics
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            from .tasks import log_firmware_download_attempt
            
            content_type = ContentType.objects.get_for_model(firmware)
            
            # Async log to avoid blocking
            log_firmware_download_attempt.delay(
                firmware_ct_id=content_type.id,
                firmware_id=str(firmware.id),
                user_id=user.id,
                status='initiated',
            )
            
        except Exception as e:
            logger.error(f"Error handling download_requested: {e}")
    
    @receiver(firmware_download_ready)
    def handle_download_ready(sender, session, **kwargs):
        """
        When download ready:
        1. Update download attempt status
        2. Send notification (already handled by storage app)
        """
        try:
            # Update download attempt if storage_session_id was logged
            from django.apps import apps
            FirmwareDownloadAttempt = apps.get_model('firmwares', 'FirmwareDownloadAttempt')
            
            if hasattr(session, 'id'):
                attempt = FirmwareDownloadAttempt.objects.filter(
                    storage_session_id=session.id
                ).first()
                
                if attempt:
                    attempt.status = 'ready'
                    attempt.save(update_fields=['status'])
            
        except Exception as e:
            logger.error(f"Error handling download_ready: {e}")
    
    @receiver(storage_quota_exhausted)
    def handle_storage_quota_exhausted(sender, drive, **kwargs):
        """
        When storage quota exhausted:
        1. Notify admins (already handled by storage)
        2. Mark firmware uploads as temporarily unavailable
        """
        logger.warning(f"Storage quota exhausted for drive: {drive.drive_name}")
        # Could pause new firmware uploads here if needed

except ImportError:
    logger.info("Core signals not available - storage integration disabled")


# === FIRMWARE MODEL SIGNALS (For Multi-Brand Schema) ===

@receiver(post_save, sender='firmwares.Brand')
def invalidate_brand_caches(sender, instance, created, **kwargs):
    """When brand created/updated, invalidate relevant caches and create blog category"""
    if created:
        from apps.pages.widgets import HomePageWidgetService
        try:
            HomePageWidgetService.invalidate_caches(['latest_firmwares'])
        except Exception as e:
            logger.warning(f"Failed to invalidate caches: {e}")
        
        # Auto-create blog category for brand
        from .blog_automation import FirmwareBlogService
        try:
            FirmwareBlogService.ensure_brand_category(instance)
            logger.info(f"Blog category created for brand: {instance.name}")
        except Exception as e:
            logger.warning(f"Failed to create blog category: {e}")


@receiver(post_save, sender='firmwares.Model')
def handle_model_created(sender, instance, created, **kwargs):
    """When model created, create blog category"""
    if created:
        from .blog_automation import FirmwareBlogService
        try:
            FirmwareBlogService.ensure_model_category(instance)
            logger.info(f"Blog category created for model: {instance.name}")
        except Exception as e:
            logger.warning(f"Failed to create blog category: {e}")


@receiver(post_save, sender='firmwares.OfficialFirmware')
@receiver(post_save, sender='firmwares.EngineeringFirmware')
@receiver(post_save, sender='firmwares.ReadbackFirmware')
@receiver(post_save, sender='firmwares.ModifiedFirmware')
@receiver(post_save, sender='firmwares.OtherFirmware')
def handle_firmware_uploaded_blog(sender, instance, created, **kwargs):
    """
    When firmware uploaded, auto-generate/update blog post for that model
    Lists all available firmwares across all variants
    Also triggers distribution to social platforms
    
    Uses Celery for async processing when available, falls back to sync.
    """
    if created and instance.model:
        try:
            # Try async via Celery first
            from django.conf import settings
            use_celery = getattr(settings, 'CELERY_BROKER_URL', None) is not None
            
            if use_celery:
                try:
                    from .tasks import generate_firmware_blog_post
                    generate_firmware_blog_post.delay(model_id=instance.model.id)
                    logger.info(f"Queued blog generation task for {instance.model.name}")
                    
                    # Also notify distribution system async
                    if apps.is_installed('apps.distribution'):
                        from apps.core.signals import content_updated
                        content_updated.send(
                            sender=sender,
                            content_type='firmware',
                            instance=instance,
                            blog_post=None,  # Will be created by task
                        )
                    return
                except ImportError:
                    pass  # Fall through to sync
            
            # Fallback: sync blog generation
            from .blog_automation import FirmwareBlogService
            post = FirmwareBlogService.generate_firmware_post(instance.model)
            if post:
                logger.info(f"Blog post auto-generated for {instance.model.name}: {post.title}")
                
                # Notify distribution system of new firmware availability
                if apps.is_installed('apps.distribution'):
                    try:
                        from apps.core.signals import content_updated
                        content_updated.send(
                            sender=sender,
                            content_type='firmware',
                            instance=instance,
                            blog_post=post,
                        )
                    except ImportError:
                        logger.debug("Core signals not available for distribution notification")
                        
        except Exception as e:
            logger.error(f"Failed to generate blog post: {e}")


@receiver(post_delete, sender='firmwares.OfficialFirmware')
@receiver(post_delete, sender='firmwares.EngineeringFirmware')
@receiver(post_delete, sender='firmwares.ReadbackFirmware')
@receiver(post_delete, sender='firmwares.ModifiedFirmware')
@receiver(post_delete, sender='firmwares.OtherFirmware')
def handle_firmware_deleted_blog(sender, instance, **kwargs):
    """When firmware deleted, update blog post to reflect changes"""
    if instance.model:
        from .blog_automation import FirmwareBlogService
        try:
            # Regenerate blog post with updated firmware list
            post = FirmwareBlogService.generate_firmware_post(instance.model, force_update=True)
            if post:
                logger.info(f"Blog post updated after firmware deletion: {post.title}")
        except Exception as e:
            logger.error(f"Failed to update blog post: {e}")


@receiver(post_save, sender='firmwares.PendingFirmware')
def handle_pending_firmware_decision(sender, instance, **kwargs):
    """
    When pending firmware approved/rejected:
    1. If approved → convert to appropriate firmware type
    2. If rejected → cleanup file
    3. Notify uploader
    """
    if instance.admin_decision == 'approved' and not kwargs.get('created'):
        # Check if already processed
        if hasattr(instance, '_processed'):
            return
        
        try:
            # Convert to appropriate firmware type based on ai_category
            from django.apps import apps
            
            category_map = {
                'official': 'OfficialFirmware',
                'engineering': 'EngineeringFirmware',
                'readback': 'ReadbackFirmware',
                'modified': 'ModifiedFirmware',
                'other': 'OtherFirmware',
            }
            
            target_model_name = category_map.get(instance.ai_category, 'OtherFirmware')
            TargetModel = apps.get_model('firmwares', target_model_name)
            
            # Create new firmware
            firmware = TargetModel.objects.create(
                original_file_name=instance.original_file_name,
                stored_file_path=instance.stored_file_path,
                uploader=instance.uploader,
                brand=instance.uploaded_brand,
                model=instance.uploaded_model,
                variant=instance.uploaded_variant,
                chipset=instance.chipset,
                partitions=instance.partitions,
                is_password_protected=instance.is_password_protected,
                encrypted_password=instance.encrypted_password,
                metadata=instance.metadata,
            )
            
            # Mark as processed
            instance._processed = True
            
            # Invalidate caches
            from apps.pages.widgets import HomePageWidgetService
            HomePageWidgetService.invalidate_caches(['latest_firmwares'])
            
            logger.info(f"Converted pending firmware {instance.id} to {target_model_name}: {firmware.id}")
            
            # Auto-generate blog post for this model if it has firmwares now
            if firmware.model:
                from .blog_automation import FirmwareBlogService
                try:
                    post = FirmwareBlogService.generate_firmware_post(firmware.model)
                    if post:
                        logger.info(f"Blog post created for approved firmware: {post.title}")
                except Exception as e:
                    logger.error(f"Failed to generate blog post for approved firmware: {e}")
            
            # Notify uploader of approval
            if instance.uploader:
                try:
                    from apps.core.signals import notification_requested
                    notification_requested.send(
                        sender=sender,
                        recipient=instance.uploader,
                        notification_type='firmware_approved',
                        title='Firmware Approved',
                        message=f'Your firmware upload "{instance.original_file_name}" has been approved.',
                        metadata={'firmware_id': str(firmware.id)}
                    )
                except Exception as e:
                    logger.warning(f"Failed to send approval notification: {e}")
            
        except Exception as e:
            logger.error(f"Error converting pending firmware: {e}")
    
    elif instance.admin_decision == 'rejected':
        # Cleanup file and notify uploader
        logger.info(f"Pending firmware rejected: {instance.id}")
        
        # Delete the stored file
        if instance.stored_file_path:
            try:
                import os
                if os.path.exists(instance.stored_file_path):
                    os.remove(instance.stored_file_path)
                    logger.info(f"Deleted rejected firmware file: {instance.stored_file_path}")
            except Exception as e:
                logger.error(f"Failed to delete rejected firmware file: {e}")
        
        # Notify uploader of rejection
        if instance.uploader:
            try:
                from apps.core.signals import notification_requested
                notification_requested.send(
                    sender=sender,
                    recipient=instance.uploader,
                    notification_type='firmware_rejected',
                    title='Firmware Rejected',
                    message=f'Your firmware upload "{instance.original_file_name}" was rejected. Reason: {instance.admin_notes or "Not specified"}',
                    metadata={'pending_id': str(instance.id)}
                )
            except Exception as e:
                logger.warning(f"Failed to send rejection notification: {e}")


# === FIRMWARE REQUEST SIGNALS ===

@receiver(post_save, sender='firmwares.FirmwareRequest')
def handle_firmware_request(sender, instance, created, **kwargs):
    """
    When firmware requested:
    1. Invalidate most_requested cache
    2. Notify admins if high urgency
    3. Check if similar firmware already exists
    """
    if created:
        # Invalidate cache
        from apps.pages.widgets import HomePageWidgetService
        HomePageWidgetService.invalidate_caches(['most_requested'])
        
        # If urgent, notify admins
        if instance.urgency >= 3:  # High or Urgent
            logger.warning(
                f"Urgent firmware request: {instance.brand}/{instance.model} "
                f"({instance.request_count} requests)"
            )
            # Send admin notification via security event
            try:
                from apps.security_events.models import SecurityEvent
                SecurityEvent.objects.create(
                    event_type='firmware_urgent_request',
                    severity='medium',
                    message=f"Urgent firmware request: {instance.brand}/{instance.model}",
                    metadata={
                        'request_id': instance.id,
                        'brand': instance.brand,
                        'model': instance.model,
                        'urgency': instance.urgency,
                        'request_count': instance.request_count,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create security event for urgent request: {e}")


# === VIEW/DOWNLOAD TRACKING (For Performance) ===
# Note: These are handled via async tasks (tasks.py) to avoid blocking HTTP responses
# Signals here would be too slow for high-traffic scenarios


# === AUTO-FILL SIGNALS ===
# Automatically fill missing firmware metadata from AI and internet sources

if FirmwareAutoFill:
    from apps.firmwares.models import Brand, Model, Variant

    @receiver(post_save, sender=Brand)
    def autofill_brand_on_create(sender, instance, created, **kwargs):
        """Auto-fill brand fields on creation"""
        if not created:
            return

        try:
            if not instance.description:
                data = FirmwareAutoFill.autofill_brand(instance.name)
                if data.get('description'):
                    instance.description = data['description']
                    instance.save(update_fields=['description'])
                    logger.info(f"Auto-filled brand: {instance.name}")
        except Exception as e:
            logger.error(f"Failed to autofill brand {instance.name}: {e}")

    @receiver(post_save, sender=Model)
    def autofill_model_on_create(sender, instance, created, **kwargs):
        """Auto-fill model fields on creation"""
        if not created:
            return

        try:
            needs_update = False
            update_fields = []

            if not instance.marketing_name:
                data = FirmwareAutoFill.autofill_model(instance.brand.name, instance.name)
                if data.get('marketing_name'):
                    instance.marketing_name = data['marketing_name']
                    update_fields.append('marketing_name')
                    needs_update = True

            if not instance.model_code:
                if 'data' not in locals():
                    data = FirmwareAutoFill.autofill_model(instance.brand.name, instance.name)
                if data.get('model_code'):
                    instance.model_code = data['model_code']
                    update_fields.append('model_code')
                    needs_update = True

            if not instance.description:
                if 'data' not in locals():
                    data = FirmwareAutoFill.autofill_model(instance.brand.name, instance.name)
                if data.get('description'):
                    instance.description = data['description']
                    update_fields.append('description')
                    needs_update = True

            if needs_update:
                instance.save(update_fields=update_fields)
                logger.info(f"Auto-filled model: {instance.brand.name} {instance.name}")
        except Exception as e:
            logger.error(f"Failed to autofill model {instance.name}: {e}")

    @receiver(post_save, sender=Variant)
    def autofill_variant_on_create(sender, instance, created, **kwargs):
        """Auto-fill variant fields on creation"""
        if not created:
            return

        try:
            needs_update = False
            update_fields = []

            if not instance.chipset:
                data = FirmwareAutoFill.autofill_variant(
                    instance.model.brand.name,
                    instance.model.name,
                    instance.region
                )
                if data.get('chipset'):
                    instance.chipset = data['chipset']
                    update_fields.append('chipset')
                    needs_update = True

            if not instance.ram_options:
                if 'data' not in locals():
                    data = FirmwareAutoFill.autofill_variant(
                        instance.model.brand.name,
                        instance.model.name,
                        instance.region
                    )
                if data.get('ram_options'):
                    instance.ram_options = data['ram_options']
                    update_fields.append('ram_options')
                    needs_update = True

            if not instance.storage_options:
                if 'data' not in locals():
                    data = FirmwareAutoFill.autofill_variant(
                        instance.model.brand.name,
                        instance.model.name,
                        instance.region
                    )
                if data.get('storage_options'):
                    instance.storage_options = data['storage_options']
                    update_fields.append('storage_options')
                    needs_update = True

            if needs_update:
                instance.save(update_fields=update_fields)
                logger.info(f"Auto-filled variant: {instance.model.brand.name} {instance.model.name} {instance.name}")
        except Exception as e:
            logger.error(f"Failed to autofill variant {instance.name}: {e}")
