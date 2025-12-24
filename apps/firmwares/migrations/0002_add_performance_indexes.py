# Generated manually for performance optimization - 2025-12-22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firmwares', '0001_initial'),
    ]

    operations = [
        # Add indexes to PendingFirmware for better query performance
        migrations.AddIndex(
            model_name='pendingfirmware',
            index=models.Index(
                fields=['uploader', '-created_at'],
                name='pending_fw_uploader_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='pendingfirmware',
            index=models.Index(
                fields=['uploaded_brand', 'uploaded_model'],
                name='pending_fw_brand_model_idx'
            ),
        ),

        # Add indexes to BaseFirmware models for download tracking
        migrations.AddIndex(
            model_name='officialfirmware',
            index=models.Index(
                fields=['brand', 'model', 'variant'],
                name='official_fw_hierarchy_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='officialfirmware',
            index=models.Index(
                fields=['-created_at'],
                name='official_fw_created_idx'
            ),
        ),
        
        migrations.AddIndex(
            model_name='engineeringfirmware',
            index=models.Index(
                fields=['brand', 'model', 'variant'],
                name='eng_fw_hierarchy_idx'
            ),
        ),
        
        migrations.AddIndex(
            model_name='modifiedfirmware',
            index=models.Index(
                fields=['brand', 'model', 'variant'],
                name='mod_fw_hierarchy_idx'
            ),
        ),
        
        # Add indexes to Brand and Model for faster lookups
        migrations.AddIndex(
            model_name='brand',
            index=models.Index(
                fields=['name'],
                name='brand_name_idx'
            ),
        ),
        
        migrations.AddIndex(
            model_name='model',
            index=models.Index(
                fields=['brand', 'name'],
                name='model_brand_name_idx'
            ),
        ),
        
        migrations.AddIndex(
            model_name='variant',
            index=models.Index(
                fields=['model', 'name'],
                name='variant_model_name_idx'
            ),
        ),
    ]

