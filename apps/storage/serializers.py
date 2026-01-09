from rest_framework import serializers

from .models import (
    DriveFileOrganization,
    FirmwareStorageLocation,
    ServiceAccount,
    SharedDriveAccount,
    UserDownloadSession,
)


class SharedDriveAccountSerializer(serializers.ModelSerializer):
    utilization_percent = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    active_service_accounts = serializers.SerializerMethodField()

    class Meta:
        model = SharedDriveAccount
        fields = [
            "id",
            "name",
            "drive_id",
            "max_files",
            "current_file_count",
            "utilization_percent",
            "available_slots",
            "total_size_gb",
            "health_status",
            "is_active",
            "priority",
            "active_service_accounts",
            "last_health_check",
        ]
        read_only_fields = ["current_file_count", "total_size_gb", "last_health_check"]

    def get_utilization_percent(self, obj):
        return round(obj.utilization_percent(), 2)

    def get_available_slots(self, obj):
        return obj.available_file_slots()

    def get_active_service_accounts(self, obj):
        return obj.service_accounts.filter(is_active=True).count()


class ServiceAccountSerializer(serializers.ModelSerializer):
    available_quota_gb = serializers.SerializerMethodField()

    class Meta:
        model = ServiceAccount
        fields = [
            "id",
            "name",
            "email",
            "shared_drive",
            "daily_quota_gb",
            "used_quota_today_gb",
            "available_quota_gb",
            "is_active",
            "is_banned",
            "consecutive_failures",
            "average_speed_mbps",
            "total_operations",
            "last_used_at",
        ]
        read_only_fields = [
            "used_quota_today_gb",
            "total_operations",
            "last_used_at",
            "average_speed_mbps",
        ]

    def get_available_quota_gb(self, obj):
        return round(obj.available_quota_gb(), 2)


class FirmwareStorageLocationSerializer(serializers.ModelSerializer):
    file_size_gb = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = FirmwareStorageLocation
        fields = [
            "id",
            "storage_type",
            "file_name",
            "file_size_bytes",
            "file_size_gb",
            "is_primary",
            "is_verified",
            "priority",
            "download_count",
            "consecutive_failures",
            "is_available",
            "created_at",
            "last_verified_at",
        ]
        read_only_fields = ["download_count", "consecutive_failures", "created_at"]

    def get_file_size_gb(self, obj):
        return round(obj.file_size_gb(), 3)

    def get_is_available(self, obj):
        return obj.is_available()


class UserDownloadSessionSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    time_remaining_seconds = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = UserDownloadSession
        fields = [
            "id",
            "status",
            "file_name",
            "file_size",
            "user_gdrive_link",
            "expires_at",
            "time_remaining_seconds",
            "is_expired",
            "error_message",
            "created_at",
            "copy_completed_at",
        ]
        read_only_fields = "__all__"

    def get_file_name(self, obj):
        return obj.storage_location.file_name if obj.storage_location else None

    def get_file_size(self, obj):
        return obj.storage_location.file_size_bytes if obj.storage_location else None

    def get_time_remaining_seconds(self, obj):
        return int(obj.time_remaining().total_seconds())

    def get_is_expired(self, obj):
        return obj.is_expired()


class DriveFileOrganizationSerializer(serializers.ModelSerializer):
    folder_path = serializers.SerializerMethodField()
    size_gb = serializers.SerializerMethodField()

    class Meta:
        model = DriveFileOrganization
        fields = [
            "id",
            "shared_drive",
            "folder_path",
            "file_count",
            "size_gb",
            "created_at",
        ]
        read_only_fields = ["file_count", "created_at"]

    def get_folder_path(self, obj):
        path_parts = [obj.brand_name]
        if obj.model_name:
            path_parts.append(obj.model_name)
        if obj.variant_name:
            path_parts.append(obj.variant_name)
        if obj.category_name:
            path_parts.append(obj.category_name)
        return "/".join(path_parts)

    def get_size_gb(self, obj):
        return round(obj.total_size_bytes / (1024**3), 3)


class InitiateDownloadSerializer(serializers.Serializer):
    """Serializer for initiating firmware download"""

    firmware_type = serializers.ChoiceField(
        choices=[
            "official",
            "engineering",
            "readback",
            "modified",
            "other",
            "unclassified",
        ],
        help_text="Type of firmware",
    )
    firmware_id = serializers.UUIDField(help_text="UUID of firmware file")


class QuotaStatusSerializer(serializers.Serializer):
    """Serializer for quota status response"""

    drive_name = serializers.CharField()
    total_quota_gb = serializers.FloatField()
    used_quota_gb = serializers.FloatField()
    available_quota_gb = serializers.FloatField()
    utilization_percent = serializers.FloatField()
    active_accounts = serializers.IntegerField()
    file_count = serializers.IntegerField()
    max_files = serializers.IntegerField()
    file_utilization_percent = serializers.FloatField()
    health_status = serializers.CharField()
