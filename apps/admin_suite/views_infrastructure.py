"""
Admin Suite Infrastructure Views - Storage & Firmwares Management

Enterprise-grade admin views for:
- Storage (Shared Drives, Service Accounts, File Management)
- Firmwares (Brands, Models, Variants, ROMs)
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_protect

from .views_shared import _ADMIN_DISABLED, _make_breadcrumb, _render_admin

logger = logging.getLogger(__name__)


# =============================================================================
# STORAGE MANAGEMENT
# =============================================================================

@csrf_protect
@staff_member_required
def admin_suite_storage(request: HttpRequest) -> HttpResponse:
    """Storage dashboard - Shared Drives, Service Accounts, Files overview."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "total_drives": 0,
        "active_drives": 0,
        "total_files": 0,
        "total_size_gb": 0,
        "service_accounts": 0,
        "healthy_drives": 0,
        "warning_drives": 0,
        "critical_drives": 0,
    }
    drives = []
    service_accounts = []
    message = ""

    # Handle POST actions
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.storage.models import ServiceAccount as SA
            from apps.storage.models import SharedDriveAccount

            if action == "toggle_drive":
                drive_id = request.POST.get("drive_id")
                drive = SharedDriveAccount.objects.filter(pk=drive_id).first()
                if drive:
                    drive.is_active = not drive.is_active
                    drive.save(update_fields=["is_active"])
                    message = f"Drive {'enabled' if drive.is_active else 'disabled'}."
            elif action == "health_check":
                drive_id = request.POST.get("drive_id")
                drive = SharedDriveAccount.objects.filter(pk=drive_id).first()
                if drive:
                    drive.update_health_status()
                    message = f"Health check completed for {drive.name}."
            elif action == "create_drive":
                name = (request.POST.get("name") or "").strip()[:128]
                drive_id_val = (request.POST.get("drive_id_value") or "").strip()[:128]
                owner_email = (request.POST.get("owner_email") or "").strip()[:255]
                if name and drive_id_val:
                    SharedDriveAccount.objects.create(
                        name=name,
                        drive_id=drive_id_val,
                        owner_email=owner_email,
                        is_active=True,
                    )
                    message = f"Drive '{name}' created."
        except Exception as exc:
            logger.warning("Storage admin action failed: %s", exc)
            message = f"Action failed: {exc}"

    # Load data
    try:
        from apps.storage.models import CloudStorageProvider, SharedDriveAccount
        from apps.storage.models import ServiceAccount as SA

        # Cloud Storage Providers
        all_providers = CloudStorageProvider.objects.all().order_by("-priority", "-is_active", "name")
        stats["total_providers"] = all_providers.count()
        stats["active_providers"] = all_providers.filter(is_active=True, status="active").count()

        providers = list(all_providers[:20].values(
            "id", "name", "provider", "auth_type", "account_email", "status",
            "is_active", "total_space_bytes", "used_space_bytes", "last_sync_at"
        ))

        # Shared Drives
        all_drives = SharedDriveAccount.objects.all().order_by("-priority", "-is_active", "name")
        stats["total_drives"] = all_drives.count()
        stats["active_drives"] = all_drives.filter(is_active=True).count()
        stats["healthy_drives"] = all_drives.filter(health_status="healthy").count()
        stats["warning_drives"] = all_drives.filter(health_status="warning").count()
        stats["critical_drives"] = all_drives.filter(health_status__in=["critical", "full"]).count()

        for d in all_drives:
            stats["total_files"] += d.current_file_count
            stats["total_size_gb"] += d.total_size_gb

        drives = list(all_drives[:50].values(
            "id", "name", "drive_id", "owner_email", "max_files", "current_file_count",
            "total_size_gb", "is_active", "health_status", "priority", "last_health_check",
            "provider__name"
        ))

        stats["service_accounts"] = SA.objects.count()
        service_accounts = list(SA.objects.all()[:50].values(
            "id", "name", "email", "is_active", "used_quota_today_gb", "daily_quota_gb"
        ))
    except Exception as exc:
        logger.debug("Failed to load storage data: %s", exc)
        providers = []

    return _render_admin(
        request,
        "admin_suite/storage.html",
        {
            "stats": stats,
            "providers": providers,
            "drives": drives,
            "service_accounts": service_accounts,
            "message": message,
        },
        nav_active="storage",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Storage", None),
        ),
        subtitle="Cloud Providers, Shared Drives & Service Accounts",
    )


@csrf_protect
@staff_member_required
def admin_suite_storage_files(request: HttpRequest) -> HttpResponse:
    """File management view - browse, search, manage stored files."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    query = (request.GET.get("q") or "").strip()
    page = max(1, int(request.GET.get("page", "1") or "1"))
    page_size = 50
    offset = (page - 1) * page_size

    files = []
    total_count = 0
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.storage.models import StoredFile

            if action == "delete_file":
                file_id = request.POST.get("file_id")
                sf = StoredFile.objects.filter(pk=file_id).first()
                if sf:
                    sf.is_deleted = True
                    sf.save(update_fields=["is_deleted"])
                    message = f"File marked as deleted."
        except Exception as exc:
            logger.warning("Storage file action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.storage.models import StoredFile

        qs = StoredFile.objects.filter(is_deleted=False).select_related("drive")
        if query:
            qs = qs.filter(original_filename__icontains=query)

        total_count = qs.count()
        files = list(qs.order_by("-created_at")[offset:offset + page_size].values(
            "id", "original_filename", "file_size", "mime_type", "checksum_sha256",
            "drive__name", "created_at", "download_count"
        ))
    except Exception as exc:
        logger.debug("Failed to load files: %s", exc)

    return _render_admin(
        request,
        "admin_suite/storage_files.html",
        {
            "files": files,
            "total_count": total_count,
            "query": query,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="storage",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Storage", "admin_suite:storage"),
            ("Files", None),
        ),
        subtitle="File Management",
    )


@csrf_protect
@staff_member_required
def admin_suite_storage_providers(request: HttpRequest) -> HttpResponse:
    """Cloud storage providers management - Add, configure, manage providers."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    providers = []
    provider_choices = []
    auth_type_choices = []

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.storage.models import CloudStorageProvider
            from apps.storage.services.provisioning import provisioner

            if action == "create_provider":
                name = (request.POST.get("name") or "").strip()[:128]
                provider_type = request.POST.get("provider_type")
                account_email = (request.POST.get("account_email") or "").strip()[:255]

                if name and provider_type:
                    provider = CloudStorageProvider.objects.create(
                        name=name,
                        provider=provider_type,
                        account_email=account_email,
                        status="pending",
                        is_active=True,
                    )
                    message = f"Provider '{name}' created. Configure credentials to activate."

            elif action == "configure_google_service_account":
                provider_id = request.POST.get("provider_id")
                sa_json = request.POST.get("service_account_json", "").strip()

                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider and sa_json:
                    try:
                        import json
                        sa_data = json.loads(sa_json)
                        result = provisioner.provision_google_service_account(
                            provider=provider,
                            service_account_info=sa_data,
                        )
                        if result.get("success"):
                            provider.service_account_json_path = result.get("credentials_path", "")
                            provider.status = "active"
                            provider.save()
                            message = f"Service account configured: {result.get('email')}"
                        else:
                            message = f"Failed: {result.get('error')}"
                    except json.JSONDecodeError:
                        message = "Invalid JSON format for service account."

            elif action == "bulk_upload_service_accounts":
                provider_id = request.POST.get("provider_id")
                sa_json_array = request.POST.get("service_accounts_json", "").strip()

                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider and sa_json_array:
                    try:
                        import json
                        sa_list = json.loads(sa_json_array)
                        if isinstance(sa_list, list):
                            result = provisioner.bulk_provision_google_service_accounts(
                                provider=provider,
                                service_accounts_json=sa_list,
                            )
                            message = f"Provisioned {result['success']}/{result['total']} service accounts."
                        else:
                            message = "Expected JSON array of service accounts."
                    except json.JSONDecodeError:
                        message = "Invalid JSON format."

            elif action == "fetch_shared_drives":
                provider_id = request.POST.get("provider_id")
                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider:
                    drives = provisioner.fetch_google_shared_drives(provider)
                    message = f"Found and synced {len(drives)} shared drives."

            elif action == "validate_connection":
                provider_id = request.POST.get("provider_id")
                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider:
                    result = provisioner.validate_provider_connection(provider)
                    if result.get("success"):
                        message = f"Connection valid. Available: {result.get('available_space_gb', 0):.2f} GB"
                    else:
                        message = f"Connection failed: {result.get('error')}"

            elif action == "toggle_provider":
                provider_id = request.POST.get("provider_id")
                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider:
                    provider.is_active = not provider.is_active
                    provider.save(update_fields=["is_active"])
                    message = f"Provider {'enabled' if provider.is_active else 'disabled'}."

            elif action == "delete_provider":
                provider_id = request.POST.get("provider_id")
                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider:
                    name = provider.name
                    provider.delete()
                    message = f"Provider '{name}' deleted."

            elif action == "configure_s3":
                provider_id = request.POST.get("provider_id")
                access_key = request.POST.get("access_key_id", "").strip()
                secret_key = request.POST.get("secret_access_key", "").strip()
                bucket = request.POST.get("bucket_name", "").strip()
                region = request.POST.get("region", "us-east-1").strip()
                endpoint = request.POST.get("endpoint_url", "").strip()

                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider and access_key and secret_key and bucket:
                    result = provisioner.provision_s3_compatible(
                        provider=provider,
                        access_key_id=access_key,
                        secret_access_key=secret_key,
                        bucket_name=bucket,
                        region=region,
                        endpoint_url=endpoint or None,
                    )
                    if result.get("success"):
                        message = f"S3 storage configured for bucket: {bucket}"
                    else:
                        message = f"Failed: {result.get('error')}"

            elif action == "configure_mega":
                provider_id = request.POST.get("provider_id")
                email = request.POST.get("mega_email", "").strip()
                password = request.POST.get("mega_password", "").strip()

                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider and email and password:
                    result = provisioner.provision_mega(
                        provider=provider,
                        email=email,
                        password=password,
                    )
                    if result.get("success"):
                        message = f"MEGA account configured: {email}"
                    else:
                        message = f"Failed: {result.get('error')}"

            elif action == "configure_onedrive":
                provider_id = request.POST.get("provider_id")
                client_id = request.POST.get("client_id", "").strip()
                client_secret = request.POST.get("client_secret", "").strip()
                tenant_id = request.POST.get("tenant_id", "common").strip()

                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider and client_id and client_secret:
                    result = provisioner.provision_onedrive(
                        provider=provider,
                        client_id=client_id,
                        client_secret=client_secret,
                        tenant_id=tenant_id,
                    )
                    if result.get("success"):
                        message = f"OneDrive configured. Auth URL: {result.get('auth_url', 'N/A')[:50]}..."
                    else:
                        message = f"Failed: {result.get('error')}"

            elif action == "configure_dropbox":
                provider_id = request.POST.get("provider_id")
                app_key = request.POST.get("app_key", "").strip()
                app_secret = request.POST.get("app_secret", "").strip()
                access_token = request.POST.get("access_token", "").strip()

                provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
                if provider and app_key and app_secret:
                    result = provisioner.provision_dropbox(
                        provider=provider,
                        app_key=app_key,
                        app_secret=app_secret,
                        access_token=access_token or None,
                    )
                    if result.get("success"):
                        message = f"Dropbox configured. Status: {result.get('status')}"
                    else:
                        message = f"Failed: {result.get('error')}"

        except Exception as exc:
            logger.warning("Storage provider action failed: %s", exc)
            message = f"Action failed: {exc}"

    # Load providers
    try:
        from apps.storage.models import CloudStorageProvider

        providers = list(CloudStorageProvider.objects.all().order_by("-is_active", "-priority", "name").values(
            "id", "name", "provider", "auth_type", "account_email", "account_id",
            "status", "is_active", "total_space_bytes", "used_space_bytes",
            "daily_transfer_limit_gb", "used_transfer_today_gb",
            "last_sync_at", "last_error", "created_at"
        ))
        provider_choices = CloudStorageProvider.PROVIDER_CHOICES
        auth_type_choices = CloudStorageProvider.AUTH_TYPE_CHOICES
    except Exception as exc:
        logger.debug("Failed to load providers: %s", exc)

    return _render_admin(
        request,
        "admin_suite/storage_providers.html",
        {
            "providers": providers,
            "provider_choices": provider_choices,
            "auth_type_choices": auth_type_choices,
            "message": message,
        },
        nav_active="storage_providers",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Storage", "admin_suite:storage"),
            ("Cloud Providers", None),
        ),
        subtitle="Cloud Storage Provider Management",
    )


@csrf_protect
@staff_member_required
def admin_suite_storage_provider_detail(request: HttpRequest, provider_id: str) -> HttpResponse:
    """Detailed view for a single cloud storage provider."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    message = ""
    provider = None
    shared_drives = []
    service_accounts = []

    try:
        from apps.storage.models import CloudStorageProvider

        provider = CloudStorageProvider.objects.filter(pk=provider_id).first()
        if not provider:
            return _render_admin(
                request,
                "admin_suite/storage_provider_detail.html",
                {"error": "Provider not found"},
                nav_active="storage",
                breadcrumb=_make_breadcrumb(
                    ("Admin Home", "admin_suite:admin_suite"),
                    ("Storage", "admin_suite:storage"),
                    ("Cloud Providers", "admin_suite:storage_providers"),
                    ("Not Found", None),
                ),
                subtitle="Provider Not Found",
            )

        # Load related data
        shared_drives = list(provider.shared_drives.all().values(
            "id", "name", "drive_id", "owner_email", "max_files",
            "current_file_count", "total_size_gb", "is_active", "health_status"
        ))

        # Get service accounts from shared drives
        for drive in provider.shared_drives.all():
            sa_list = list(drive.service_accounts.all()[:20].values(
                "id", "name", "email", "is_active", "is_banned",
                "used_quota_today_gb", "daily_quota_gb", "last_used_at"
            ))
            service_accounts.extend(sa_list)

    except Exception as exc:
        logger.debug("Failed to load provider detail: %s", exc)
        message = f"Error loading provider: {exc}"

    return _render_admin(
        request,
        "admin_suite/storage_provider_detail.html",
        {
            "provider": provider,
            "shared_drives": shared_drives,
            "service_accounts": service_accounts,
            "message": message,
        },
        nav_active="storage_providers",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Storage", "admin_suite:storage"),
            ("Cloud Providers", "admin_suite:storage_providers"),
            (provider.name if provider else "Detail", None),
        ),
        subtitle=f"Provider: {provider.name}" if provider else "Provider Detail",
    )


# =============================================================================
# FIRMWARES MANAGEMENT
# =============================================================================

@csrf_protect
@staff_member_required
def admin_suite_firmwares(request: HttpRequest) -> HttpResponse:
    """Firmwares dashboard - Brands, Models, Variants, ROMs overview."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "total_brands": 0,
        "total_models": 0,
        "total_variants": 0,
        "total_roms": 0,
        "pending_brand_requests": 0,
        "pending_model_requests": 0,
        "pending_variant_requests": 0,
    }
    recent_brands = []
    recent_models = []
    pending_requests = []
    message = ""

    # Handle POST actions
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.firmwares.models import (
                Brand,
                BrandCreationRequest,
                Model,
                ModelCreationRequest,
                Variant,
            )

            if action == "approve_brand":
                req_id = request.POST.get("request_id")
                bcr = BrandCreationRequest.objects.filter(pk=req_id, status="pending").first()
                if bcr:
                    from django.utils.text import slugify
                    Brand.objects.create(name=bcr.name, slug=slugify(bcr.name))
                    bcr.status = "approved"
                    bcr.reviewed_by = request.user
                    bcr.save(update_fields=["status", "reviewed_by", "reviewed_at"])
                    message = f"Brand '{bcr.name}' approved and created."
            elif action == "reject_brand":
                req_id = request.POST.get("request_id")
                bcr = BrandCreationRequest.objects.filter(pk=req_id, status="pending").first()
                if bcr:
                    bcr.status = "rejected"
                    bcr.reviewed_by = request.user
                    bcr.notes = request.POST.get("notes", "")
                    bcr.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes"])
                    message = f"Brand request rejected."
            elif action == "create_brand":
                name = (request.POST.get("name") or "").strip()[:128]
                if name:
                    from django.utils.text import slugify
                    Brand.objects.create(name=name, slug=slugify(name))
                    message = f"Brand '{name}' created."
            elif action == "create_model":
                brand_id = request.POST.get("brand_id")
                name = (request.POST.get("name") or "").strip()[:128]
                if brand_id and name:
                    from django.utils.text import slugify
                    brand = Brand.objects.filter(pk=brand_id).first()
                    if brand:
                        Model.objects.create(brand=brand, name=name, slug=slugify(name))
                        message = f"Model '{name}' created for {brand.name}."
        except Exception as exc:
            logger.warning("Firmwares admin action failed: %s", exc)
            message = f"Action failed: {exc}"

    # Load data
    try:
        from apps.firmwares.models import (
            Brand,
            BrandCreationRequest,
            Model,
            ModelCreationRequest,
            Variant,
            VariantCreationRequest,
        )

        stats["total_brands"] = Brand.objects.count()
        stats["total_models"] = Model.objects.count()
        stats["total_variants"] = Variant.objects.count()
        stats["pending_brand_requests"] = BrandCreationRequest.objects.filter(status="pending").count()
        stats["pending_model_requests"] = ModelCreationRequest.objects.filter(status="pending").count()
        stats["pending_variant_requests"] = VariantCreationRequest.objects.filter(status="pending").count()

        # Try to get ROM count
        try:
            from apps.firmwares.models import StockROM
            stats["total_roms"] = StockROM.objects.count()
        except Exception as exc:
            logger.debug("Failed to count stock ROMs: %s", exc)

        recent_brands = list(Brand.objects.order_by("-created_at")[:10].values("id", "name", "slug", "created_at"))
        recent_models = list(Model.objects.select_related("brand").order_by("-created_at")[:10].values(
            "id", "name", "slug", "brand__name", "created_at"
        ))

        # Pending requests
        pending_brand_reqs = list(BrandCreationRequest.objects.filter(status="pending").order_by("-created_at")[:10].values(
            "id", "name", "created_at", "requested_by__email"
        ))
        pending_model_reqs = list(ModelCreationRequest.objects.filter(status="pending").order_by("-created_at")[:10].values(
            "id", "name", "brand__name", "created_at", "requested_by__email"
        ))
        pending_requests = [
            {"type": "brand", **r} for r in pending_brand_reqs
        ] + [
            {"type": "model", **r} for r in pending_model_reqs
        ]
    except Exception as exc:
        logger.debug("Failed to load firmwares data: %s", exc)

    return _render_admin(
        request,
        "admin_suite/firmwares.html",
        {
            "stats": stats,
            "recent_brands": recent_brands,
            "recent_models": recent_models,
            "pending_requests": pending_requests,
            "message": message,
        },
        nav_active="firmwares",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Firmwares", None),
        ),
        subtitle="Brands, Models & ROMs",
    )


@csrf_protect
@staff_member_required
def admin_suite_firmwares_brands(request: HttpRequest) -> HttpResponse:
    """Detailed brand management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    query = (request.GET.get("q") or "").strip()
    page = max(1, int(request.GET.get("page", "1") or "1"))
    page_size = 50
    offset = (page - 1) * page_size

    brands = []
    total_count = 0
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from django.utils.text import slugify

            from apps.firmwares.models import Brand

            if action == "create":
                name = (request.POST.get("name") or "").strip()[:128]
                if name:
                    Brand.objects.create(name=name, slug=slugify(name))
                    message = f"Brand '{name}' created."
            elif action == "delete":
                brand_id = request.POST.get("brand_id")
                Brand.objects.filter(pk=brand_id).delete()
                message = "Brand deleted."
            elif action == "update":
                brand_id = request.POST.get("brand_id")
                name = (request.POST.get("name") or "").strip()[:128]
                if brand_id and name:
                    Brand.objects.filter(pk=brand_id).update(name=name, slug=slugify(name))
                    message = "Brand updated."
        except Exception as exc:
            logger.warning("Brand action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from django.db.models import Count

        from apps.firmwares.models import Brand

        qs = Brand.objects.annotate(model_count=Count("models"))
        if query:
            qs = qs.filter(name__icontains=query)

        total_count = qs.count()
        brands = list(qs.order_by("name")[offset:offset + page_size].values(
            "id", "name", "slug", "model_count", "created_at"
        ))
    except Exception as exc:
        logger.debug("Failed to load brands: %s", exc)

    return _render_admin(
        request,
        "admin_suite/firmwares_brands.html",
        {
            "brands": brands,
            "total_count": total_count,
            "query": query,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="firmwares",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Firmwares", "admin_suite:firmwares"),
            ("Brands", None),
        ),
        subtitle="Brand Management",
    )


@csrf_protect
@staff_member_required
def admin_suite_firmwares_models(request: HttpRequest) -> HttpResponse:
    """Detailed model management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    query = (request.GET.get("q") or "").strip()
    brand_filter = (request.GET.get("brand") or "").strip()
    page = max(1, int(request.GET.get("page", "1") or "1"))
    page_size = 50
    offset = (page - 1) * page_size

    models_list = []
    brands = []
    total_count = 0
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from django.utils.text import slugify

            from apps.firmwares.models import Brand, Model

            if action == "create":
                brand_id = request.POST.get("brand_id")
                name = (request.POST.get("name") or "").strip()[:128]
                brand = Brand.objects.filter(pk=brand_id).first()
                if brand and name:
                    Model.objects.create(brand=brand, name=name, slug=slugify(name))
                    message = f"Model '{name}' created."
            elif action == "delete":
                model_id = request.POST.get("model_id")
                Model.objects.filter(pk=model_id).delete()
                message = "Model deleted."
        except Exception as exc:
            logger.warning("Model action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from django.db.models import Count

        from apps.firmwares.models import Brand, Model

        brands = list(Brand.objects.order_by("name").values("id", "name"))

        qs = Model.objects.select_related("brand").annotate(variant_count=Count("variants"))
        if query:
            qs = qs.filter(name__icontains=query)
        if brand_filter:
            qs = qs.filter(brand_id=brand_filter)

        total_count = qs.count()
        models_list = list(qs.order_by("brand__name", "name")[offset:offset + page_size].values(
            "id", "name", "slug", "brand__id", "brand__name", "variant_count", "created_at"
        ))
    except Exception as exc:
        logger.debug("Failed to load models: %s", exc)

    return _render_admin(
        request,
        "admin_suite/firmwares_models.html",
        {
            "models": models_list,
            "brands": brands,
            "total_count": total_count,
            "query": query,
            "brand_filter": brand_filter,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="firmwares",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Firmwares", "admin_suite:firmwares"),
            ("Models", None),
        ),
        subtitle="Model Management",
    )


# =============================================================================
# ENHANCED ADS MANAGEMENT
# =============================================================================

@csrf_protect
@staff_member_required
def admin_suite_ads_campaigns(request: HttpRequest) -> HttpResponse:
    """Campaign management for ads."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    campaigns = []
    message = ""
    query = (request.GET.get("q") or "").strip()
    page = max(1, int(request.GET.get("page", "1") or "1"))
    page_size = 20
    offset = (page - 1) * page_size

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ads.models import Campaign

            if action == "create":
                name = (request.POST.get("name") or "").strip()[:255]
                if name:
                    Campaign.objects.create(
                        name=name,
                        is_active=bool(request.POST.get("is_active")),
                    )
                    message = f"Campaign '{name}' created."
            elif action == "toggle":
                campaign_id = request.POST.get("campaign_id")
                camp = Campaign.objects.filter(pk=campaign_id).first()
                if camp:
                    camp.is_active = not camp.is_active
                    camp.save(update_fields=["is_active"])
                    message = f"Campaign {'activated' if camp.is_active else 'deactivated'}."
            elif action == "delete":
                campaign_id = request.POST.get("campaign_id")
                Campaign.objects.filter(pk=campaign_id).delete()
                message = "Campaign deleted."
        except Exception as exc:
            logger.warning("Campaign action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.ads.models import Campaign

        qs = Campaign.objects.all()
        if query:
            qs = qs.filter(name__icontains=query)

        total_count = qs.count()
        campaigns = list(qs.order_by("-created_at")[offset:offset + page_size].values(
            "id", "name", "is_active", "budget", "spent", "start_date", "end_date", "created_at"
        ))
    except Exception as exc:
        logger.debug("Failed to load campaigns: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ads_campaigns.html",
        {
            "campaigns": campaigns,
            "query": query,
            "page": page,
            "page_size": page_size,
            "message": message,
        },
        nav_active="ads",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Ads", "admin_suite:ads"),
            ("Campaigns", None),
        ),
        subtitle="Campaign Management",
    )


@csrf_protect
@staff_member_required
def admin_suite_ads_placements(request: HttpRequest) -> HttpResponse:
    """Detailed placement management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    placements = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ads.models import AdPlacement

            if action == "create":
                name = (request.POST.get("name") or "").strip()[:255]
                slug = (request.POST.get("slug") or "").strip()[:255]
                page_context = (request.POST.get("page_context") or "").strip()[:255]
                if name and slug:
                    AdPlacement.objects.create(
                        name=name,
                        slug=slug,
                        page_context=page_context,
                        is_active=True,
                        is_enabled=True,
                    )
                    message = f"Placement '{name}' created."
            elif action == "toggle":
                placement_id = request.POST.get("placement_id")
                pl = AdPlacement.objects.filter(pk=placement_id).first()
                if pl:
                    pl.is_active = not pl.is_active
                    pl.save(update_fields=["is_active"])
                    message = f"Placement {'activated' if pl.is_active else 'deactivated'}."
            elif action == "delete":
                placement_id = request.POST.get("placement_id")
                AdPlacement.objects.filter(pk=placement_id).update(is_deleted=True)
                message = "Placement deleted."
        except Exception as exc:
            logger.warning("Placement action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.ads.models import AdPlacement

        placements = list(AdPlacement.objects.filter(is_deleted=False).order_by("name").values(
            "id", "name", "slug", "page_context", "is_active", "is_enabled",
            "allowed_types", "allowed_sizes", "created_at"
        ))
    except Exception as exc:
        logger.debug("Failed to load placements: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ads_placements.html",
        {
            "placements": placements,
            "message": message,
        },
        nav_active="ads",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Ads", "admin_suite:ads"),
            ("Placements", None),
        ),
        subtitle="Placement Management",
    )


@csrf_protect
@staff_member_required
def admin_suite_ads_creatives(request: HttpRequest) -> HttpResponse:
    """Creative assets management."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    creatives = []
    message = ""

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            from apps.ads.models import AdCreative

            if action == "toggle":
                creative_id = request.POST.get("creative_id")
                cr = AdCreative.objects.filter(pk=creative_id).first()
                if cr:
                    cr.is_active = not cr.is_active
                    cr.save(update_fields=["is_active"])
                    message = f"Creative {'activated' if cr.is_active else 'deactivated'}."
        except Exception as exc:
            logger.warning("Creative action failed: %s", exc)
            message = f"Action failed: {exc}"

    try:
        from apps.ads.models import AdCreative

        creatives = list(AdCreative.objects.filter(is_deleted=False).order_by("-created_at")[:100].values(
            "id", "name", "creative_type", "is_active", "is_enabled", "created_at"
        ))
    except Exception as exc:
        logger.debug("Failed to load creatives: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ads_creatives.html",
        {
            "creatives": creatives,
            "message": message,
        },
        nav_active="ads",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Ads", "admin_suite:ads"),
            ("Creatives", None),
        ),
        subtitle="Creative Assets",
    )


@csrf_protect
@staff_member_required
def admin_suite_ads_analytics(request: HttpRequest) -> HttpResponse:
    """Ads analytics and reporting."""
    if not getattr(settings, "ADMIN_SUITE_ENABLED", True):
        raise _ADMIN_DISABLED

    stats = {
        "total_impressions": 0,
        "total_clicks": 0,
        "ctr": 0,
        "impressions_24h": 0,
        "clicks_24h": 0,
        "impressions_7d": 0,
        "clicks_7d": 0,
    }
    top_placements = []
    recent_events = []

    try:
        from django.db.models import Count
        from django.utils import timezone

        from apps.ads.models import AdEvent, AdPlacement

        now = timezone.now()
        day_ago = now - timezone.timedelta(hours=24)
        week_ago = now - timezone.timedelta(days=7)

        stats["total_impressions"] = AdEvent.objects.filter(event_type="impression").count()
        stats["total_clicks"] = AdEvent.objects.filter(event_type="click").count()
        stats["impressions_24h"] = AdEvent.objects.filter(event_type="impression", created_at__gte=day_ago).count()
        stats["clicks_24h"] = AdEvent.objects.filter(event_type="click", created_at__gte=day_ago).count()
        stats["impressions_7d"] = AdEvent.objects.filter(event_type="impression", created_at__gte=week_ago).count()
        stats["clicks_7d"] = AdEvent.objects.filter(event_type="click", created_at__gte=week_ago).count()

        if stats["total_impressions"] > 0:
            stats["ctr"] = round((stats["total_clicks"] / stats["total_impressions"]) * 100, 2)

        top_placements = list(
            AdPlacement.objects.filter(is_deleted=False)
            .annotate(event_count=Count("events"))
            .order_by("-event_count")[:10]
            .values("id", "name", "slug", "event_count")
        )

        recent_events = list(
            AdEvent.objects.select_related("placement")
            .order_by("-created_at")[:50]
            .values("id", "event_type", "placement__name", "created_at")
        )
    except Exception as exc:
        logger.debug("Failed to load ads analytics: %s", exc)

    return _render_admin(
        request,
        "admin_suite/ads_analytics.html",
        {
            "stats": stats,
            "top_placements": top_placements,
            "recent_events": recent_events,
        },
        nav_active="ads",
        breadcrumb=_make_breadcrumb(
            ("Admin Home", "admin_suite:admin_suite"),
            ("Ads", "admin_suite:ads"),
            ("Analytics", None),
        ),
        subtitle="Performance Analytics",
    )


__all__ = [
    # Storage
    'admin_suite_storage',
    'admin_suite_storage_files',
    # Firmwares
    'admin_suite_firmwares',
    'admin_suite_firmwares_brands',
    'admin_suite_firmwares_models',
    # Ads Enhanced
    'admin_suite_ads_campaigns',
    'admin_suite_ads_placements',
    'admin_suite_ads_creatives',
    'admin_suite_ads_analytics',
]
