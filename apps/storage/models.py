from __future__ import annotations

import uuid
import json
import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet


def get_encryption_key():
    """Get or create encryption key for credentials."""
    key_path = os.path.join(settings.BASE_DIR, '.credentials_key')
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    with open(key_path, 'wb') as f:
        f.write(key)
    return key


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CloudStorageProvider(Timestamped):
    """
    Cloud storage provider configuration with encrypted credentials.
    Supports Google Drive, OneDrive, Dropbox, MEGA, etc.
    Auto-creates service accounts and fetches necessary JSON config files.
    """
    PROVIDER_CHOICES = [
        ('google_drive', 'Google Drive'),
        ('google_shared_drive', 'Google Shared Drive'),
        ('onedrive', 'OneDrive / SharePoint'),
        ('dropbox', 'Dropbox'),
        ('mega', 'MEGA'),
        ('box', 'Box'),
        ('s3', 'Amazon S3'),
        ('azure_blob', 'Azure Blob Storage'),
        ('backblaze', 'Backblaze B2'),
        ('wasabi', 'Wasabi'),
        ('ftp', 'FTP/SFTP'),
        ('webdav', 'WebDAV'),
    ]
    
    AUTH_TYPE_CHOICES = [
        ('oauth2', 'OAuth 2.0'),
        ('service_account', 'Service Account (JSON Key)'),
        ('api_key', 'API Key'),
        ('access_token', 'Access Token'),
        ('username_password', 'Username & Password'),
        ('ssh_key', 'SSH Key'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Setup'),
        ('configuring', 'Configuring'),
        ('active', 'Active'),
        ('error', 'Error'),
        ('suspended', 'Suspended'),
        ('quota_exceeded', 'Quota Exceeded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, help_text="Display name for this storage account")
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    auth_type = models.CharField(max_length=32, choices=AUTH_TYPE_CHOICES, default='oauth2')
    
    # Account identification
    account_email = models.EmailField(blank=True, help_text="Primary account email")
    account_id = models.CharField(max_length=255, blank=True, help_text="Provider-specific account ID")
    
    # Encrypted credentials storage
    _credentials_encrypted = models.BinaryField(blank=True, null=True, db_column='credentials_encrypted')
    
    # OAuth2 tokens (encrypted)
    _access_token_encrypted = models.BinaryField(blank=True, null=True, db_column='access_token_encrypted')
    _refresh_token_encrypted = models.BinaryField(blank=True, null=True, db_column='refresh_token_encrypted')
    token_expiry = models.DateTimeField(null=True, blank=True)
    
    # Service Account JSON path
    service_account_json_path = models.CharField(max_length=512, blank=True, help_text="Path to service account JSON file")
    
    # Configuration
    root_folder_id = models.CharField(max_length=255, blank=True, help_text="Root folder ID for storage")
    team_drive_id = models.CharField(max_length=255, blank=True, help_text="Team/Shared drive ID if applicable")
    bucket_name = models.CharField(max_length=255, blank=True, help_text="S3/Cloud bucket name")
    region = models.CharField(max_length=64, blank=True, help_text="Cloud region")
    endpoint_url = models.URLField(max_length=512, blank=True, help_text="Custom endpoint URL")
    
    # Status & health
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    
    # Quotas & limits
    total_space_bytes = models.BigIntegerField(default=0, help_text="Total storage space")
    used_space_bytes = models.BigIntegerField(default=0, help_text="Used storage space")
    daily_transfer_limit_gb = models.FloatField(default=750, help_text="Daily transfer quota in GB")
    used_transfer_today_gb = models.FloatField(default=0, help_text="Used transfer today")
    transfer_reset_at = models.DateTimeField(null=True, blank=True)
    
    # Service accounts linked to this provider
    max_service_accounts = models.IntegerField(default=100, help_text="Max service accounts allowed")
    auto_provision_service_accounts = models.BooleanField(default=True, help_text="Auto-create service accounts")
    
    # Priority for load balancing
    priority = models.IntegerField(default=0, help_text="Higher priority = preferred for uploads")
    
    notes = models.TextField(blank=True, default="")
    
    class Meta:
        ordering = ['-priority', '-is_active', 'name']
        verbose_name = "Cloud Storage Provider"
        verbose_name_plural = "Cloud Storage Providers"
    
    def _get_cipher(self):
        """Get Fernet cipher for encryption/decryption."""
        return Fernet(get_encryption_key())
    
    def set_credentials(self, credentials_dict: dict):
        """Encrypt and store credentials."""
        cipher = self._get_cipher()
        data = json.dumps(credentials_dict).encode()
        self._credentials_encrypted = cipher.encrypt(data)
    
    def get_credentials(self) -> dict:
        """Decrypt and return credentials."""
        if not self._credentials_encrypted:
            return {}
        cipher = self._get_cipher()
        try:
            data = cipher.decrypt(bytes(self._credentials_encrypted))
            return json.loads(data.decode())
        except Exception:
            return {}
    
    def set_access_token(self, token: str):
        """Encrypt and store access token."""
        if not token:
            self._access_token_encrypted = None
            return
        cipher = self._get_cipher()
        self._access_token_encrypted = cipher.encrypt(token.encode())
    
    def get_access_token(self) -> str:
        """Decrypt and return access token."""
        if not self._access_token_encrypted:
            return ""
        cipher = self._get_cipher()
        try:
            return cipher.decrypt(bytes(self._access_token_encrypted)).decode()
        except Exception:
            return ""
    
    def set_refresh_token(self, token: str):
        """Encrypt and store refresh token."""
        if not token:
            self._refresh_token_encrypted = None
            return
        cipher = self._get_cipher()
        self._refresh_token_encrypted = cipher.encrypt(token.encode())
    
    def get_refresh_token(self) -> str:
        """Decrypt and return refresh token."""
        if not self._refresh_token_encrypted:
            return ""
        cipher = self._get_cipher()
        try:
            return cipher.decrypt(bytes(self._refresh_token_encrypted)).decode()
        except Exception:
            return ""
    
    def available_space_gb(self):
        """Calculate available space in GB."""
        if self.total_space_bytes == 0:
            return float('inf')
        return (self.total_space_bytes - self.used_space_bytes) / (1024 ** 3)
    
    def usage_percent(self):
        """Calculate usage percentage."""
        if self.total_space_bytes == 0:
            return 0
        return (self.used_space_bytes / self.total_space_bytes) * 100
    
    def is_token_expired(self):
        """Check if OAuth token is expired."""
        if not self.token_expiry:
            return True
        return timezone.now() >= self.token_expiry
    
    def can_accept_transfer(self, size_gb: float = 0) -> bool:
        """Check if provider can accept a transfer."""
        if not self.is_active or self.status not in ('active', 'configuring'):
            return False
        
        # Check daily quota
        if self.daily_transfer_limit_gb > 0:
            available = self.daily_transfer_limit_gb - self.used_transfer_today_gb
            if available < size_gb:
                return False
        
        # Check storage space
        if self.total_space_bytes > 0:
            available_space = (self.total_space_bytes - self.used_space_bytes) / (1024 ** 3)
            if available_space < size_gb:
                return False
        
        return True
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_display()}) - {self.status}"


class SharedDriveAccount(Timestamped):
    """
    Google Shared Drive configuration
    Each drive has 400,000 file limit and costs $10-12/month
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to parent provider account
    provider = models.ForeignKey(
        CloudStorageProvider,
        on_delete=models.CASCADE,
        related_name='shared_drives',
        null=True,
        blank=True,
        help_text="Parent cloud storage provider account"
    )
    
    name = models.CharField(max_length=128, help_text="e.g., SharedDrive_1, SharedDrive_2, SharedDrive_3")
    drive_id = models.CharField(max_length=128, unique=True, help_text="Google Drive ID")
    owner_email = models.EmailField(help_text="Account owner email")
    
    # File limit tracking (400,000 files per drive)
    max_files = models.IntegerField(default=400000, help_text="Maximum files allowed per shared drive")
    current_file_count = models.IntegerField(default=0, help_text="Current number of files in drive")
    total_size_gb = models.FloatField(default=0.0, help_text="Total storage used in GB")
    
    # Health & status
    is_active = models.BooleanField(default=True)
    health_status = models.CharField(
        max_length=32,
        choices=[
            ('healthy', 'Healthy'),
            ('warning', 'Warning - Near Limit'),
            ('critical', 'Critical - At Limit'),
            ('full', 'Full'),
            ('offline', 'Offline')
        ],
        default='healthy'
    )
    last_health_check = models.DateTimeField(null=True, blank=True)
    
    # Smart placement priority (higher = preferred for new uploads)
    priority = models.IntegerField(default=0, help_text="Higher priority drives are filled first")
    notes = models.TextField(blank=True, default="")
    
    class Meta:
        ordering = ['-priority', '-is_active', 'current_file_count']
        verbose_name = "Shared Drive Account"
        verbose_name_plural = "Shared Drive Accounts"
    
    def available_file_slots(self):
        """Calculate remaining file slots"""
        return max(0, self.max_files - self.current_file_count)
    
    def utilization_percent(self):
        """Calculate utilization percentage"""
        if self.max_files == 0:
            return 0
        return (self.current_file_count / self.max_files) * 100
    
    def can_accept_files(self, file_count=1):
        """Check if drive can accept more files"""
        return (
            self.is_active and 
            self.health_status != 'full' and
            self.available_file_slots() >= file_count
        )
    
    def update_health_status(self):
        """Update health status based on utilization"""
        utilization = self.utilization_percent()
        
        if not self.is_active:
            self.health_status = 'offline'
        elif utilization >= 100:
            self.health_status = 'full'
        elif utilization >= 95:
            self.health_status = 'critical'
        elif utilization >= 80:
            self.health_status = 'warning'
        else:
            self.health_status = 'healthy'
        
        self.last_health_check = timezone.now()
        self.save(update_fields=['health_status', 'last_health_check'])
    
    def __str__(self):
        return f"{self.name} ({self.current_file_count}/{self.max_files} files, {self.health_status})"


class ServiceAccount(Timestamped):
    """
    Google Service Account for API operations
    100 service accounts per shared drive
    Each has 750GB/day upload/download quota
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shared_drive = models.ForeignKey(
        SharedDriveAccount, 
        on_delete=models.CASCADE, 
        related_name='service_accounts'
    )
    name = models.CharField(max_length=128, help_text="e.g., SA_1_001, SA_2_045")
    email = models.EmailField(unique=True, help_text="Service account email")
    credentials_path = models.CharField(max_length=512, help_text="Path to JSON key file")
    
    # Quota tracking (750GB/day per account)
    daily_quota_gb = models.IntegerField(default=750, help_text="Daily transfer quota in GB")
    used_quota_today_gb = models.FloatField(default=0.0, help_text="Used quota today in GB")
    quota_reset_at = models.DateTimeField(help_text="When quota resets (daily)")
    
    # Performance metrics
    is_active = models.BooleanField(default=True)
    is_banned = models.BooleanField(default=False, help_text="If Google suspended this account")
    consecutive_failures = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    average_speed_mbps = models.FloatField(default=0.0, help_text="Average transfer speed")
    total_operations = models.BigIntegerField(default=0, help_text="Total API operations")
    total_bytes_transferred = models.BigIntegerField(default=0)
    
    class Meta:
        ordering = ['used_quota_today_gb', '-average_speed_mbps']
        unique_together = ('shared_drive', 'email')
        verbose_name = "Service Account"
        verbose_name_plural = "Service Accounts"
    
    def available_quota_gb(self):
        """Calculate available quota, reset if past midnight"""
        now = timezone.now()
        if now > self.quota_reset_at:
            self.used_quota_today_gb = 0.0
            self.quota_reset_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timezone.timedelta(days=1)
            self.save(update_fields=['used_quota_today_gb', 'quota_reset_at'])
        
        return self.daily_quota_gb - self.used_quota_today_gb
    
    def can_handle_transfer(self, size_gb):
        """Check if account can handle a transfer"""
        return (
            self.is_active and
            not self.is_banned and
            self.consecutive_failures < 3 and
            self.available_quota_gb() >= size_gb
        )
    
    def __str__(self):
        return f"{self.name} ({self.available_quota_gb():.1f}GB available)"


class FirmwareStorageLocation(Timestamped):
    """
    Maps firmware files to their storage location(s)
    Supports multiple storage backends and fallbacks
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to firmware (using GenericForeignKey for flexibility)
    content_type = models.ForeignKey(
        'contenttypes.ContentType',
        on_delete=models.CASCADE,
        help_text="Type of firmware (OfficialFirmware, ModifiedFirmware, etc.)"
    )
    object_id = models.UUIDField(help_text="Firmware UUID")
    # content_object = GenericForeignKey('content_type', 'object_id')  # Uncomment if needed
    
    # Storage type
    storage_type = models.CharField(
        max_length=32,
        choices=[
            ('shared_drive', 'Google Shared Drive'),
            ('external_link', 'External Provider'),
            ('user_temp', 'User GDrive (Temporary)')
        ]
    )
    
    # Google Drive fields
    shared_drive = models.ForeignKey(
        SharedDriveAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='stored_files'
    )
    gdrive_file_id = models.CharField(max_length=128, blank=True, help_text="Google Drive file ID")
    gdrive_folder_path = models.CharField(max_length=512, blank=True, help_text="Folder path in drive")
    
    # External provider fields
    external_provider = models.CharField(
        max_length=64, 
        blank=True,
        choices=[
            ('mediafire', 'MediaFire'),
            ('mega', 'MEGA'),
            ('dropbox', 'Dropbox'),
            ('onedrive', 'OneDrive'),
            ('direct_http', 'Direct HTTP'),
            ('torrent', 'Torrent'),
            ('other', 'Other')
        ]
    )
    external_url = models.URLField(max_length=1024, blank=True)
    external_expiry = models.DateTimeField(null=True, blank=True)
    external_password = models.CharField(max_length=256, blank=True)
    
    # File metadata
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField()
    md5_hash = models.CharField(max_length=32, blank=True)
    sha256_hash = models.CharField(max_length=64, blank=True)
    
    # Priority & health
    is_primary = models.BooleanField(default=False, help_text="Primary download source")
    is_verified = models.BooleanField(default=False, help_text="File integrity verified")
    priority = models.IntegerField(default=0, help_text="Higher priority sources used first")
    last_verified_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0, help_text="Number of downloads")
    
    class Meta:
        ordering = ['-is_primary', '-priority', 'storage_type']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['storage_type', 'is_primary']),
            models.Index(fields=['gdrive_file_id']),
        ]
        verbose_name = "Firmware Storage Location"
        verbose_name_plural = "Firmware Storage Locations"
    
    def file_size_gb(self):
        """Get file size in GB"""
        return self.file_size_bytes / (1024 ** 3)
    
    def is_available(self):
        """Check if storage location is available"""
        if self.storage_type == 'external_link':
            if self.external_expiry and self.external_expiry < timezone.now():
                return False
        
        if self.storage_type == 'shared_drive' and self.shared_drive:
            if not self.shared_drive.is_active:
                return False
        
        return self.consecutive_failures < 5
    
    def __str__(self):
        return f"{self.file_name} @ {self.storage_type}"


class UserDownloadSession(Timestamped):
    """
    Temporary copy of firmware to user's personal GDrive
    Link expires after configurable TTL (24h default)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Link to firmware storage
    storage_location = models.ForeignKey(
        FirmwareStorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        related_name='download_sessions'
    )
    
    # Service account used for copy operation
    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # User's GDrive copy
    user_gdrive_file_id = models.CharField(max_length=128, blank=True)
    user_gdrive_link = models.URLField(max_length=1024, blank=True)
    
    # Lifecycle
    copy_initiated_at = models.DateTimeField(auto_now_add=True)
    copy_completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(help_text="Link expires after this time")
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=32,
        choices=[
            ('pending', 'Pending Copy'),
            ('copying', 'Copying to User Drive'),
            ('ready', 'Ready for Download'),
            ('downloading', 'User Downloading'),
            ('completed', 'Download Completed'),
            ('expired', 'Expired'),
            ('deleted', 'Deleted from User Drive'),
            ('failed', 'Copy Failed')
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True, default="")
    
    # Download tracking
    download_started_at = models.DateTimeField(null=True, blank=True)
    download_completed_at = models.DateTimeField(null=True, blank=True)
    bytes_downloaded = models.BigIntegerField(default=0)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['status', 'expires_at']),
        ]
        verbose_name = "User Download Session"
        verbose_name_plural = "User Download Sessions"
    
    def is_expired(self):
        """Check if session has expired"""
        return timezone.now() > self.expires_at
    
    def time_remaining(self):
        """Get time remaining until expiry"""
        if self.is_expired():
            return timezone.timedelta(0)
        return self.expires_at - timezone.now()
    
    def __str__(self):
        return f"{self.user.username} → {self.storage_location.file_name if self.storage_location else 'N/A'} ({self.status})"


class ServiceAccountQuotaLog(models.Model):
    """
    Daily quota usage analytics per service account
    """
    service_account = models.ForeignKey(ServiceAccount, on_delete=models.CASCADE)
    date = models.DateField()
    total_bytes_transferred = models.BigIntegerField(default=0)
    total_operations = models.IntegerField(default=0)
    peak_usage_hour = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(23)]
    )
    
    class Meta:
        unique_together = ('service_account', 'date')
        ordering = ['-date']
        verbose_name = "Service Account Quota Log"
        verbose_name_plural = "Service Account Quota Logs"
    
    def __str__(self):
        gb_transferred = self.total_bytes_transferred / (1024 ** 3)
        return f"{self.service_account.name} - {self.date}: {gb_transferred:.2f}GB"


class DriveFileOrganization(Timestamped):
    """
    Tracks folder structure organization in shared drives
    Organized by: Brand/Model/Variant/Category
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shared_drive = models.ForeignKey(SharedDriveAccount, on_delete=models.CASCADE)
    
    # Hierarchy
    brand_name = models.CharField(max_length=128)
    brand_folder_id = models.CharField(max_length=128, blank=True)
    
    model_name = models.CharField(max_length=128, blank=True)
    model_folder_id = models.CharField(max_length=128, blank=True)
    
    variant_name = models.CharField(max_length=128, blank=True)
    variant_folder_id = models.CharField(max_length=128, blank=True)
    
    category_name = models.CharField(max_length=64, blank=True)
    category_folder_id = models.CharField(max_length=128, blank=True)
    
    # Stats
    file_count = models.IntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)
    
    class Meta:
        unique_together = ('shared_drive', 'brand_name', 'model_name', 'variant_name', 'category_name')
        ordering = ['shared_drive', 'brand_name', 'model_name', 'variant_name']
        verbose_name = "Drive File Organization"
        verbose_name_plural = "Drive File Organizations"
    
    def __str__(self):
        path_parts = [self.brand_name]
        if self.model_name:
            path_parts.append(self.model_name)
        if self.variant_name:
            path_parts.append(self.variant_name)
        if self.category_name:
            path_parts.append(self.category_name)
        
        return f"{self.shared_drive.name}: {'/'.join(path_parts)}"
