# Generated manually for performance optimization - 2025-12-22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0001_cloud_storage_provider'),
    ]

    operations = [
        # Add indexes to UserDownloadSession for better query performance
        migrations.AddIndex(
            model_name='userdownloadsession',
            index=models.Index(
                fields=['user', 'status', '-created_at'],
                name='download_session_user_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='userdownloadsession',
            index=models.Index(
                fields=['status', 'created_at'],
                name='download_session_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='userdownloadsession',
            index=models.Index(
                fields=['service_account', '-created_at'],
                name='download_session_sa_idx'
            ),
        ),
        
        # Add indexes to ServiceAccount for quota management
        migrations.AddIndex(
            model_name='serviceaccount',
            index=models.Index(
                fields=['shared_drive', 'is_active', 'is_banned'],
                name='service_account_drive_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='serviceaccount',
            index=models.Index(
                fields=['is_active', 'used_quota_today_gb'],
                name='service_account_quota_idx'
            ),
        ),
        
        # Add indexes to SharedDriveAccount for load balancing
        migrations.AddIndex(
            model_name='shareddriveaccount',
            index=models.Index(
                fields=['is_active', 'total_size_gb'],
                name='shared_drive_usage_idx'
            ),
        ),
        
        # Add indexes to FirmwareStorageLocation for faster lookups
        migrations.AddIndex(
            model_name='firmwarestoragelocation',
            index=models.Index(
                fields=['content_type', 'object_id'],
                name='firmware_storage_ct_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='firmwarestoragelocation',
            index=models.Index(
                fields=['shared_drive', 'is_primary'],
                name='firmware_storage_drive_idx'
            ),
        ),
    ]

