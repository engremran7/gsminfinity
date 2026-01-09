from __future__ import annotations

import logging

from django.db import transaction

from ..models import DriveFileOrganization, FirmwareStorageLocation, SharedDriveAccount

logger = logging.getLogger(__name__)


class SmartPlacementAlgorithm:
    """
    Intelligently places firmware files across 3 shared drives
    respecting 400,000 file limit per drive

    Strategy:
    1. Organize by hierarchy: Brand/Model/Variant/Category
    2. Distribute large brands across multiple drives
    3. Keep related files together when possible
    4. Balance utilization across drives
    """

    def __init__(self):
        self.warning_threshold = 0.80  # 80% capacity
        self.critical_threshold = 0.95  # 95% capacity

    def select_optimal_drive(
        self,
        brand_name: str,
        model_name: str = None,
        variant_name: str = None,
        category: str = None,
        file_count: int = 1,
    ) -> SharedDriveAccount | None:
        """
        Select best shared drive for new firmware upload

        Priority Logic:
        1. Check if brand already exists in a drive (keep together)
        2. If brand doesn't exist, use drive with lowest utilization
        3. Respect 400k file limit (with safety margin)
        4. Skip full or unhealthy drives

        Args:
            brand_name: Firmware brand
            model_name: Optional model name
            variant_name: Optional variant name
            category: Optional category (official, modified, etc.)
            file_count: Number of files to upload

        Returns:
            SharedDriveAccount or None if no suitable drive found
        """

        # Step 1: Check if brand exists in any drive
        existing_org = (
            DriveFileOrganization.objects.filter(
                brand_name=brand_name, shared_drive__is_active=True
            )
            .select_related("shared_drive")
            .first()
        )

        if existing_org:
            drive = existing_org.shared_drive

            # Verify drive can accept more files
            if drive.can_accept_files(file_count):
                logger.info(f"Placing in existing brand location: {drive.name}")
                return drive
            else:
                logger.warning(
                    f"Brand exists in {drive.name} but drive is full, finding alternative"
                )

        # Step 2: Find drive with available capacity
        available_drives = SharedDriveAccount.objects.filter(
            is_active=True, health_status__in=["healthy", "warning"]
        ).order_by("-priority", "current_file_count")

        for drive in available_drives:
            if drive.can_accept_files(file_count):
                # Check if within safe threshold
                projected_count = drive.current_file_count + file_count
                projected_utilization = projected_count / drive.max_files

                if projected_utilization < self.critical_threshold:
                    logger.info(
                        f"Selected {drive.name} (utilization: {drive.utilization_percent():.1f}%, "
                        f"projected: {projected_utilization * 100:.1f}%)"
                    )
                    return drive

        # No suitable drive found
        logger.error(
            f"No suitable drive found for brand={brand_name}, file_count={file_count}"
        )
        return None

    def get_or_create_folder_structure(
        self,
        shared_drive: SharedDriveAccount,
        brand_name: str,
        model_name: str = None,
        variant_name: str = None,
        category: str = None,
    ) -> tuple[DriveFileOrganization, bool]:
        """
        Get or create folder organization structure
        Returns: (DriveFileOrganization, created)
        """

        org, created = DriveFileOrganization.objects.get_or_create(
            shared_drive=shared_drive,
            brand_name=brand_name,
            model_name=model_name or "",
            variant_name=variant_name or "",
            category_name=category or "",
            defaults={"file_count": 0, "total_size_bytes": 0},
        )

        return org, created

    @transaction.atomic
    def record_file_placement(
        self,
        shared_drive: SharedDriveAccount,
        brand_name: str,
        file_size_bytes: int,
        model_name: str = None,
        variant_name: str = None,
        category: str = None,
    ):
        """
        Record file placement and update counters
        """

        # Update shared drive counters
        shared_drive.current_file_count += 1
        shared_drive.total_size_gb += file_size_bytes / (1024**3)
        shared_drive.save(update_fields=["current_file_count", "total_size_gb"])

        # Update folder organization stats
        org, _ = self.get_or_create_folder_structure(
            shared_drive, brand_name, model_name, variant_name, category
        )
        org.file_count += 1
        org.total_size_bytes += file_size_bytes
        org.save(update_fields=["file_count", "total_size_bytes"])

        # Update health status
        shared_drive.update_health_status()

        logger.info(
            f"Recorded file in {shared_drive.name}: {brand_name}"
            f"{f'/{model_name}' if model_name else ''}"
            f" (Total: {shared_drive.current_file_count}/{shared_drive.max_files})"
        )

    @transaction.atomic
    def record_file_deletion(self, storage_location: FirmwareStorageLocation):
        """
        Record file deletion and update counters
        """
        if (
            storage_location.storage_type != "shared_drive"
            or not storage_location.shared_drive
        ):
            return

        shared_drive = storage_location.shared_drive

        # Update shared drive counters
        shared_drive.current_file_count = max(0, shared_drive.current_file_count - 1)
        shared_drive.total_size_gb = max(
            0, shared_drive.total_size_gb - storage_location.file_size_gb()
        )
        shared_drive.save(update_fields=["current_file_count", "total_size_gb"])

        # Update health status
        shared_drive.update_health_status()

        logger.info(
            f"Recorded deletion from {shared_drive.name}: {storage_location.file_name} "
            f"(Remaining: {shared_drive.current_file_count}/{shared_drive.max_files})"
        )

    def balance_drives(self) -> dict:
        """
        Analyze drive balance and suggest rebalancing if needed

        Returns dict with recommendations
        """
        drives = SharedDriveAccount.objects.filter(is_active=True).order_by("name")

        analysis = {
            "total_drives": drives.count(),
            "drives": [],
            "needs_rebalancing": False,
            "recommendations": [],
        }

        for drive in drives:
            utilization = drive.utilization_percent()

            drive_info = {
                "name": drive.name,
                "file_count": drive.current_file_count,
                "max_files": drive.max_files,
                "utilization_percent": utilization,
                "health_status": drive.health_status,
                "size_gb": drive.total_size_gb,
            }

            analysis["drives"].append(drive_info)

            # Check for imbalance
            if utilization > 90:
                analysis["needs_rebalancing"] = True
                analysis["recommendations"].append(
                    f"{drive.name} is at {utilization:.1f}% capacity - consider redistributing files"
                )

        # Check variance in utilization
        if len(analysis["drives"]) > 1:
            utilizations = [d["utilization_percent"] for d in analysis["drives"]]
            variance = max(utilizations) - min(utilizations)

            if variance > 30:  # More than 30% difference
                analysis["needs_rebalancing"] = True
                analysis["recommendations"].append(
                    f"High variance in utilization ({variance:.1f}%) - consider balancing"
                )

        return analysis

    def get_brand_distribution(self) -> list[dict]:
        """
        Get distribution of brands across drives
        """

        orgs = (
            DriveFileOrganization.objects.filter(
                model_name="",  # Root brand level
                variant_name="",
                category_name="",
            )
            .select_related("shared_drive")
            .order_by("brand_name")
        )

        distribution = []
        for org in orgs:
            distribution.append(
                {
                    "brand": org.brand_name,
                    "drive": org.shared_drive.name,
                    "file_count": org.file_count,
                    "size_gb": org.total_size_bytes / (1024**3),
                }
            )

        return distribution

    def suggest_migration(
        self, from_drive_id: str, to_drive_id: str, brand_name: str
    ) -> dict:
        """
        Suggest migration of brand from one drive to another
        """
        try:
            from_drive = SharedDriveAccount.objects.get(id=from_drive_id)
            to_drive = SharedDriveAccount.objects.get(id=to_drive_id)
        except SharedDriveAccount.DoesNotExist:
            return {"error": "Drive not found"}

        # Get all files for this brand
        brand_files = FirmwareStorageLocation.objects.filter(
            storage_type="shared_drive",
            shared_drive=from_drive,
            gdrive_folder_path__startswith=brand_name,
        )

        total_files = brand_files.count()
        total_size = sum(f.file_size_bytes for f in brand_files)

        # Check if target drive can accept
        can_accept = to_drive.can_accept_files(total_files)

        return {
            "from_drive": from_drive.name,
            "to_drive": to_drive.name,
            "brand": brand_name,
            "file_count": total_files,
            "total_size_gb": total_size / (1024**3),
            "can_migrate": can_accept,
            "target_utilization_after": (
                (to_drive.current_file_count + total_files) / to_drive.max_files * 100
            )
            if can_accept
            else None,
        }
