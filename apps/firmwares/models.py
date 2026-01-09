from __future__ import annotations

import uuid
from django.conf import settings
from django.db import models
from .constants import MAIN_CATEGORIES


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Brand(Timestamped):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    def __str__(self):
        return self.name


class Model(Timestamped):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=128, help_text="Device model name (e.g., Galaxy S23)")
    slug = models.SlugField(max_length=160)

    # Marketing & identification
    marketing_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Official marketing name (e.g., Samsung Galaxy S23 Ultra)"
    )
    model_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Internal model code (e.g., SM-S911B)"
    )
    description = models.TextField(blank=True, default="", help_text="Model description for SEO")

    # Specifications
    release_date = models.DateField(null=True, blank=True, help_text="Official release date")
    is_active = models.BooleanField(default=True, help_text="Is this model still supported?")

    class Meta:
        unique_together = ("brand", "slug")
        indexes = [
            models.Index(fields=['brand', 'is_active'], name='model_brand_active_idx'),
            models.Index(fields=['model_code'], name='model_code_idx'),
        ]

    def __str__(self):
        return f"{self.brand}/{self.name}"


class Variant(Timestamped):
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=128, help_text="Variant name (e.g., Global, US, EU)")
    slug = models.SlugField(max_length=160)

    # Identification
    region = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Region code (e.g., SM, EU, US, CN)"
    )
    board_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Board ID for hardware identification"
    )

    # Chipset information
    chipset = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Primary chipset (e.g., Snapdragon 8 Gen 2)"
    )

    # Specifications
    ram_options = models.JSONField(
        default=list,
        blank=True,
        help_text="Available RAM options (e.g., [4, 6, 8, 12])"
    )
    storage_options = models.JSONField(
        default=list,
        blank=True,
        help_text="Available storage options (e.g., [64, 128, 256, 512])"
    )

    # Status
    is_active = models.BooleanField(default=True, help_text="Is this variant still supported?")

    class Meta:
        unique_together = ("model", "slug")
        indexes = [
            models.Index(fields=['model', 'is_active'], name='variant_model_active_idx'),
            models.Index(fields=['chipset'], name='variant_chipset_idx'),
            models.Index(fields=['region'], name='variant_region_idx'),
        ]

    def __str__(self):
        return f"{self.model}/{self.name}"


class BrandSchema(Timestamped):
    brand = models.OneToOneField(Brand, on_delete=models.CASCADE, related_name="schema")
    schema_json = models.JSONField(default=dict)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)


class SchemaUpdateProposal(Timestamped):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="schema_proposals")
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    schema_json = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=[("pending", "pending"), ("approved", "approved"), ("rejected", "rejected")], default="pending"
    )
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")


class BrandCreationRequest(Timestamped):
    name = models.CharField(max_length=128)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ai_suggestion = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=[("pending", "pending"), ("approved", "approved"), ("rejected", "rejected")], default="pending"
    )
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")


class ModelCreationRequest(Timestamped):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ai_suggestion = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=[("pending", "pending"), ("approved", "approved"), ("rejected", "rejected")], default="pending"
    )
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")


class VariantCreationRequest(Timestamped):
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ai_suggestion = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=[("pending", "pending"), ("approved", "approved"), ("rejected", "rejected")], default="pending"
    )
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")


class PendingFirmware(Timestamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_file_name = models.CharField(max_length=255)
    stored_file_path = models.CharField(max_length=500)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    uploaded_model = models.ForeignKey(Model, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    uploaded_variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    ai_brand = models.CharField(max_length=128, blank=True, default="")
    ai_model = models.CharField(max_length=128, blank=True, default="")
    ai_variant = models.CharField(max_length=128, blank=True, default="")
    ai_category = models.CharField(max_length=32, choices=MAIN_CATEGORIES, blank=True, null=True)
    ai_subtype = models.CharField(max_length=64, blank=True, null=True)
    chipset = models.CharField(max_length=128, blank=True, default="")
    partitions = models.JSONField(default=list, blank=True)
    is_password_protected = models.BooleanField(default=False)
    encrypted_password = models.CharField(max_length=512, blank=True, default="")
    password_validation_status = models.CharField(
        max_length=32, choices=[("unknown", "unknown"), ("valid", "valid"), ("invalid", "invalid")], default="unknown"
    )
    extraction_status = models.CharField(max_length=32, choices=[("pending", "pending"), ("success", "success"), ("failed", "failed")], default="pending")
    metadata = models.JSONField(default=dict, blank=True)
    admin_decision = models.CharField(
        max_length=32, choices=[("pending", "pending"), ("approved", "approved"), ("rejected", "rejected")], default="pending"
    )
    admin_notes = models.TextField(blank=True, default="")
    category_locked = models.BooleanField(default=False)

    def __str__(self):
        # Use AI-detected or uploaded fields to create meaningful representation
        brand = self.ai_brand or (getattr(self.uploaded_brand, 'name', 'Unknown Brand') if self.uploaded_brand else "Unknown Brand")
        model = self.ai_model or (getattr(self.uploaded_model, 'name', 'Unknown Model') if self.uploaded_model else "Unknown Model")
        variant = self.ai_variant or (getattr(self.uploaded_variant, 'name', '') if self.uploaded_variant else "")
        
        if variant:
            return f"{brand} {model} ({variant})"
        return f"{brand} {model}"


class BaseFirmware(Timestamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_file_name = models.CharField(max_length=255, help_text="Original filename")
    stored_file_path = models.CharField(max_length=500, help_text="Storage path in system")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    # Hierarchy
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name="%(class)s_firmware")
    model = models.ForeignKey(Model, on_delete=models.SET_NULL, null=True, related_name="%(class)s_firmware")
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True, related_name="%(class)s_firmware")

    # Technical details
    chipset = models.CharField(max_length=128, blank=True, default="", help_text="Chipset/Processor")
    android_version = models.CharField(max_length=32, blank=True, default="", help_text="Android version (e.g., 14.0)")
    security_patch = models.DateField(null=True, blank=True, help_text="Security patch date")
    build_date = models.DateField(null=True, blank=True, help_text="Build date")
    build_number = models.CharField(max_length=128, blank=True, default="", help_text="Build number/version")

    # File information
    file_size = models.BigIntegerField(null=True, blank=True, help_text="File size in bytes")
    file_hash = models.CharField(max_length=256, blank=True, default="", help_text="SHA256 hash")

    # Structure
    partitions = models.JSONField(default=list, blank=True, help_text="Partition list")

    # Security
    is_password_protected = models.BooleanField(default=False)
    encrypted_password = models.CharField(max_length=512, blank=True, default="")

    # Metadata & tracking
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    download_count = models.PositiveIntegerField(default=0, help_text="Total downloads")
    view_count = models.PositiveIntegerField(default=0, help_text="Total views")

    # Status
    is_verified = models.BooleanField(default=False, help_text="Verified by admin")
    is_active = models.BooleanField(default=True, help_text="Available for download")

    class Meta:
        abstract = True


class OfficialFirmware(BaseFirmware):
    class Meta:
        indexes = [
            models.Index(fields=['brand', 'model', 'variant'], name='off_hierarchy_idx'),
            models.Index(fields=['chipset'], name='off_chipset_idx'),
            models.Index(fields=['android_version'], name='off_android_idx'),
            models.Index(fields=['is_verified', 'is_active'], name='off_status_idx'),
            models.Index(fields=['-created_at'], name='off_created_idx'),
        ]


class EngineeringFirmware(BaseFirmware):
    subtype = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=['brand', 'model', 'variant'], name='eng_hierarchy_idx'),
            models.Index(fields=['chipset'], name='eng_chipset_idx'),
            models.Index(fields=['android_version'], name='eng_android_idx'),
            models.Index(fields=['is_verified', 'is_active'], name='eng_status_idx'),
            models.Index(fields=['-created_at'], name='eng_created_idx'),
        ]


class ReadbackFirmware(BaseFirmware):
    class Meta:
        indexes = [
            models.Index(fields=['brand', 'model', 'variant'], name='rb_hierarchy_idx'),
            models.Index(fields=['chipset'], name='rb_chipset_idx'),
            models.Index(fields=['android_version'], name='rb_android_idx'),
            models.Index(fields=['is_verified', 'is_active'], name='rb_status_idx'),
            models.Index(fields=['-created_at'], name='rb_created_idx'),
        ]


class ModifiedFirmware(BaseFirmware):
    subtype = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=['brand', 'model', 'variant'], name='mod_hierarchy_idx'),
            models.Index(fields=['chipset'], name='mod_chipset_idx'),
            models.Index(fields=['android_version'], name='mod_android_idx'),
            models.Index(fields=['is_verified', 'is_active'], name='mod_status_idx'),
            models.Index(fields=['-created_at'], name='mod_created_idx'),
        ]


class OtherFirmware(BaseFirmware):
    subtype = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=['brand', 'model', 'variant'], name='oth_hierarchy_idx'),
            models.Index(fields=['chipset'], name='oth_chipset_idx'),
            models.Index(fields=['android_version'], name='oth_android_idx'),
            models.Index(fields=['is_verified', 'is_active'], name='oth_status_idx'),
            models.Index(fields=['-created_at'], name='oth_created_idx'),
        ]


class UnclassifiedFirmware(BaseFirmware):
    reason = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=['brand', 'model', 'variant'], name='unc_hierarchy_idx'),
            models.Index(fields=['chipset'], name='unc_chipset_idx'),
            models.Index(fields=['android_version'], name='unc_android_idx'),
            models.Index(fields=['is_verified', 'is_active'], name='unc_status_idx'),
            models.Index(fields=['-created_at'], name='unc_created_idx'),
        ]


# Import tracking models (kept separate for cleaner organization)
from .tracking_models import (
    FirmwareView,
    FirmwareDownloadAttempt,
    FirmwareRequest,
    FirmwareStats,
)
