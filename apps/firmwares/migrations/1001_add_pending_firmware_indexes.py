# Generated migration for adding performance indexes to PendingFirmware

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firmwares', '1000_remove_brand_brand_name_idx_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='pendingfirmware',
            index=models.Index(fields=['admin_decision', '-created_at'], name='pend_decision_created_idx'),
        ),
        migrations.AddIndex(
            model_name='pendingfirmware',
            index=models.Index(fields=['extraction_status'], name='pend_extraction_idx'),
        ),
        migrations.AddIndex(
            model_name='pendingfirmware',
            index=models.Index(fields=['uploader', 'admin_decision', '-created_at'], name='pend_uploader_decision_idx'),
        ),
    ]
