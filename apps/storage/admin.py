from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import (
    SharedDriveAccount,
    ServiceAccount,
    FirmwareStorageLocation,
    UserDownloadSession,
    ServiceAccountQuotaLog,
    DriveFileOrganization
)


@admin.register(SharedDriveAccount)
class SharedDriveAccountAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'drive_id_short', 'current_file_count', 'max_files',
        'utilization_badge', 'total_size_gb', 'health_status_badge',
        'priority', 'is_active', 'service_account_count'
    ]
    list_filter = ['health_status', 'is_active', 'priority']
    search_fields = ['name', 'drive_id', 'owner_email']
    readonly_fields = [
        'current_file_count', 'total_size_gb', 'last_health_check',
        'utilization_display', 'available_slots_display'
    ]
    ordering = ['-priority', '-is_active', 'current_file_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'drive_id', 'owner_email', 'priority')
        }),
        ('Capacity & Utilization', {
            'fields': (
                'max_files', 'current_file_count', 'available_slots_display',
                'utilization_display', 'total_size_gb'
            )
        }),
        ('Health & Status', {
            'fields': ('is_active', 'health_status', 'last_health_check')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )
    
    def drive_id_short(self, obj):
        return f"{obj.drive_id[:20]}..." if len(obj.drive_id) > 20 else obj.drive_id
    drive_id_short.short_description = 'Drive ID'
    
    def utilization_badge(self, obj):
        percent = obj.utilization_percent()
        if percent >= 95:
            color = 'red'
        elif percent >= 80:
            color = 'orange'
        elif percent >= 60:
            color = 'yellow'
        else:
            color = 'green'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{:.1f}%</span>',
            color, percent
        )
    utilization_badge.short_description = 'Utilization'
    
    def health_status_badge(self, obj):
        colors = {
            'healthy': 'green',
            'warning': 'orange',
            'critical': 'red',
            'full': 'darkred',
            'offline': 'gray'
        }
        color = colors.get(obj.health_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.health_status.upper()
        )
    health_status_badge.short_description = 'Health'
    
    def service_account_count(self, obj):
        return obj.service_accounts.filter(is_active=True).count()
    service_account_count.short_description = 'Active SAs'
    
    def utilization_display(self, obj):
        return f"{obj.utilization_percent():.2f}%"
    utilization_display.short_description = 'Utilization %'
    
    def available_slots_display(self, obj):
        return f"{obj.available_file_slots():,} files"
    available_slots_display.short_description = 'Available Slots'
    
    actions = ['update_health_status', 'reset_file_counts']
    
    def update_health_status(self, request, queryset):
        for drive in queryset:
            drive.update_health_status()
        self.message_user(request, f"Updated health status for {queryset.count()} drives")
    update_health_status.short_description = "Update health status"
    
    def reset_file_counts(self, request, queryset):
        queryset.update(current_file_count=0, total_size_gb=0.0)
        self.message_user(request, f"Reset file counts for {queryset.count()} drives")
    reset_file_counts.short_description = "Reset file counts (use with caution)"


@admin.register(ServiceAccount)
class ServiceAccountAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'shared_drive', 'email_short', 'quota_badge',
        'average_speed_mbps', 'total_operations', 'is_active',
        'is_banned', 'consecutive_failures', 'last_used_display'
    ]
    list_filter = ['shared_drive', 'is_active', 'is_banned', 'consecutive_failures']
    search_fields = ['name', 'email']
    readonly_fields = [
        'used_quota_today_gb', 'total_operations', 'total_bytes_transferred',
        'last_used_at', 'available_quota_display', 'quota_reset_at'
    ]
    ordering = ['shared_drive', 'used_quota_today_gb']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('shared_drive', 'name', 'email', 'credentials_path')
        }),
        ('Quota Management', {
            'fields': (
                'daily_quota_gb', 'used_quota_today_gb', 'available_quota_display',
                'quota_reset_at'
            )
        }),
        ('Performance & Health', {
            'fields': (
                'is_active', 'is_banned', 'consecutive_failures',
                'average_speed_mbps', 'last_used_at'
            )
        }),
        ('Statistics', {
            'fields': ('total_operations', 'total_bytes_transferred'),
            'classes': ('collapse',)
        })
    )
    
    def email_short(self, obj):
        return f"{obj.email[:30]}..." if len(obj.email) > 30 else obj.email
    email_short.short_description = 'Email'
    
    def quota_badge(self, obj):
        available = obj.available_quota_gb()
        percent_used = ((obj.daily_quota_gb - available) / obj.daily_quota_gb) * 100
        
        if percent_used >= 90:
            color = 'red'
        elif percent_used >= 70:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{:.1f} GB</span>',
            color, available
        )
    quota_badge.short_description = 'Available Quota'
    
    def available_quota_display(self, obj):
        return f"{obj.available_quota_gb():.2f} GB"
    available_quota_display.short_description = 'Available Quota'
    
    def last_used_display(self, obj):
        if not obj.last_used_at:
            return "Never"
        delta = timezone.now() - obj.last_used_at
        if delta.days > 0:
            return f"{delta.days}d ago"
        hours = delta.seconds // 3600
        if hours > 0:
            return f"{hours}h ago"
        minutes = (delta.seconds % 3600) // 60
        return f"{minutes}m ago"
    last_used_display.short_description = 'Last Used'
    
    actions = ['reset_quota', 'activate_accounts', 'deactivate_accounts']
    
    def reset_quota(self, request, queryset):
        queryset.update(used_quota_today_gb=0.0, consecutive_failures=0)
        self.message_user(request, f"Reset quota for {queryset.count()} service accounts")
    reset_quota.short_description = "Reset quota usage"
    
    def activate_accounts(self, request, queryset):
        queryset.update(is_active=True, consecutive_failures=0)
        self.message_user(request, f"Activated {queryset.count()} service accounts")
    activate_accounts.short_description = "Activate selected accounts"
    
    def deactivate_accounts(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} service accounts")
    deactivate_accounts.short_description = "Deactivate selected accounts"


@admin.register(FirmwareStorageLocation)
class FirmwareStorageLocationAdmin(admin.ModelAdmin):
    list_display = [
        'file_name', 'storage_type', 'shared_drive', 'file_size_display',
        'is_primary', 'is_verified', 'priority', 'download_count',
        'consecutive_failures'
    ]
    list_filter = ['storage_type', 'is_primary', 'is_verified', 'external_provider']
    search_fields = ['file_name', 'gdrive_file_id', 'external_url']
    readonly_fields = ['download_count', 'last_verified_at', 'file_size_display']
    ordering = ['-is_primary', '-priority', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('content_type', 'object_id', 'storage_type', 'file_name')
        }),
        ('Google Drive Storage', {
            'fields': ('shared_drive', 'gdrive_file_id', 'gdrive_folder_path'),
            'classes': ('collapse',)
        }),
        ('External Provider', {
            'fields': (
                'external_provider', 'external_url', 'external_expiry',
                'external_password'
            ),
            'classes': ('collapse',)
        }),
        ('File Metadata', {
            'fields': (
                'file_size_bytes', 'file_size_display', 'md5_hash', 'sha256_hash'
            )
        }),
        ('Priority & Health', {
            'fields': (
                'is_primary', 'is_verified', 'priority', 'last_verified_at',
                'consecutive_failures', 'download_count'
            )
        })
    )
    
    def file_size_display(self, obj):
        size_gb = obj.file_size_bytes / (1024 ** 3)
        if size_gb >= 1:
            return f"{size_gb:.2f} GB"
        size_mb = obj.file_size_bytes / (1024 ** 2)
        return f"{size_mb:.2f} MB"
    file_size_display.short_description = 'File Size'


@admin.register(UserDownloadSession)
class UserDownloadSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'user', 'file_name_display', 'status_badge',
        'created_at', 'expires_at', 'time_remaining_display',
        'service_account'
    ]
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['user__username', 'user__email', 'storage_location__file_name']
    readonly_fields = [
        'copy_initiated_at', 'copy_completed_at', 'download_started_at',
        'download_completed_at', 'deleted_at', 'bytes_downloaded',
        'time_remaining_display'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'storage_location', 'service_account', 'status')
        }),
        ('Google Drive Copy', {
            'fields': ('user_gdrive_file_id', 'user_gdrive_link')
        }),
        ('Lifecycle', {
            'fields': (
                'copy_initiated_at', 'copy_completed_at', 'expires_at',
                'time_remaining_display', 'deleted_at'
            )
        }),
        ('Download Tracking', {
            'fields': (
                'download_started_at', 'download_completed_at', 'bytes_downloaded'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'error_message'),
            'classes': ('collapse',)
        })
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def file_name_display(self, obj):
        if obj.storage_location:
            name = obj.storage_location.file_name
            return f"{name[:40]}..." if len(name) > 40 else name
        return "N/A"
    file_name_display.short_description = 'File'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'copying': 'blue',
            'ready': 'green',
            'downloading': 'lightblue',
            'completed': 'darkgreen',
            'expired': 'orange',
            'deleted': 'red',
            'failed': 'darkred'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'
    
    def time_remaining_display(self, obj):
        remaining = obj.time_remaining()
        if remaining.total_seconds() <= 0:
            return "EXPIRED"
        
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        
        if remaining.days > 0:
            return f"{remaining.days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    time_remaining_display.short_description = 'Time Remaining'
    
    actions = ['cleanup_expired', 'delete_from_drive']
    
    def cleanup_expired(self, request, queryset):
        expired = queryset.filter(expires_at__lt=timezone.now(), status='ready')
        count = expired.count()
        expired.update(status='expired')
        self.message_user(request, f"Marked {count} sessions as expired")
    cleanup_expired.short_description = "Mark expired sessions"
    
    def delete_from_drive(self, request, queryset):
        # This would trigger Celery task to delete from GDrive
        count = queryset.count()
        self.message_user(request, f"Queued {count} sessions for deletion")
    delete_from_drive.short_description = "Queue for drive deletion"


@admin.register(ServiceAccountQuotaLog)
class ServiceAccountQuotaLogAdmin(admin.ModelAdmin):
    list_display = [
        'service_account', 'date', 'bytes_transferred_display',
        'total_operations', 'peak_usage_hour'
    ]
    list_filter = ['date', 'service_account__shared_drive']
    search_fields = ['service_account__name']
    date_hierarchy = 'date'
    ordering = ['-date', 'service_account']
    
    def bytes_transferred_display(self, obj):
        gb = obj.total_bytes_transferred / (1024 ** 3)
        return f"{gb:.2f} GB"
    bytes_transferred_display.short_description = 'Data Transferred'


@admin.register(DriveFileOrganization)
class DriveFileOrganizationAdmin(admin.ModelAdmin):
    list_display = [
        'shared_drive', 'path_display', 'file_count',
        'size_display', 'created_at'
    ]
    list_filter = ['shared_drive', 'brand_name', 'category_name']
    search_fields = ['brand_name', 'model_name', 'variant_name']
    readonly_fields = ['file_count', 'total_size_bytes']
    ordering = ['shared_drive', 'brand_name', 'model_name', 'variant_name']
    
    def path_display(self, obj):
        path_parts = [obj.brand_name]
        if obj.model_name:
            path_parts.append(obj.model_name)
        if obj.variant_name:
            path_parts.append(obj.variant_name)
        if obj.category_name:
            path_parts.append(obj.category_name)
        
        return " / ".join(path_parts)
    path_display.short_description = 'Folder Path'
    
    def size_display(self, obj):
        gb = obj.total_size_bytes / (1024 ** 3)
        if gb >= 1:
            return f"{gb:.2f} GB"
        mb = obj.total_size_bytes / (1024 ** 2)
        return f"{mb:.2f} MB"
    size_display.short_description = 'Total Size'


# Import timezone for last_used_display method
from django.utils import timezone
