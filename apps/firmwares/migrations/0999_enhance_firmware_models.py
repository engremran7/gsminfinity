# Generated migration for enhanced firmware models

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('firmwares', '0002_add_performance_indexes'),
    ]

    operations = [
        # Model enhancements
        migrations.AddField(
            model_name='model',
            name='marketing_name',
            field=models.CharField(blank=True, default='', help_text='Official marketing name (e.g., Samsung Galaxy S23 Ultra)', max_length=255),
        ),
        migrations.AddField(
            model_name='model',
            name='model_code',
            field=models.CharField(blank=True, default='', help_text='Internal model code (e.g., SM-S911B)', max_length=64),
        ),
        migrations.AddField(
            model_name='model',
            name='description',
            field=models.TextField(blank=True, default='', help_text='Model description for SEO'),
        ),
        migrations.AddField(
            model_name='model',
            name='release_date',
            field=models.DateField(blank=True, help_text='Official release date', null=True),
        ),
        migrations.AddField(
            model_name='model',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Is this model still supported?'),
        ),
        migrations.AddIndex(
            model_name='model',
            index=models.Index(fields=['brand', 'is_active'], name='model_brand_active_idx'),
        ),
        migrations.AddIndex(
            model_name='model',
            index=models.Index(fields=['model_code'], name='model_code_idx'),
        ),
        
        # Variant enhancements
        migrations.AddField(
            model_name='variant',
            name='chipset',
            field=models.CharField(blank=True, default='', help_text='Primary chipset (e.g., Snapdragon 8 Gen 2)', max_length=128),
        ),
        migrations.AddField(
            model_name='variant',
            name='ram_options',
            field=models.JSONField(blank=True, default=list, help_text='Available RAM options (e.g., [4, 6, 8, 12])'),
        ),
        migrations.AddField(
            model_name='variant',
            name='storage_options',
            field=models.JSONField(blank=True, default=list, help_text='Available storage options (e.g., [64, 128, 256, 512])'),
        ),
        migrations.AddField(
            model_name='variant',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Is this variant still supported?'),
        ),
        migrations.AddIndex(
            model_name='variant',
            index=models.Index(fields=['model', 'is_active'], name='variant_model_active_idx'),
        ),
        migrations.AddIndex(
            model_name='variant',
            index=models.Index(fields=['chipset'], name='variant_chipset_idx'),
        ),
        migrations.AddIndex(
            model_name='variant',
            index=models.Index(fields=['region'], name='variant_region_idx'),
        ),
        
        # BaseFirmware enhancements (applied to all firmware types)
        migrations.AddField(
            model_name='officialfirmware',
            name='android_version',
            field=models.CharField(blank=True, default='', help_text='Android version (e.g., 14.0)', max_length=32),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='security_patch',
            field=models.DateField(blank=True, help_text='Security patch date', null=True),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='build_date',
            field=models.DateField(blank=True, help_text='Build date', null=True),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='build_number',
            field=models.CharField(blank=True, default='', help_text='Build number/version', max_length=128),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='file_size',
            field=models.BigIntegerField(blank=True, help_text='File size in bytes', null=True),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='file_hash',
            field=models.CharField(blank=True, default='', help_text='SHA256 hash', max_length=256),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='download_count',
            field=models.PositiveIntegerField(default=0, help_text='Total downloads'),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='view_count',
            field=models.PositiveIntegerField(default=0, help_text='Total views'),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='is_verified',
            field=models.BooleanField(default=False, help_text='Verified by admin'),
        ),
        migrations.AddField(
            model_name='officialfirmware',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Available for download'),
        ),
    ]

