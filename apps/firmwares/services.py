import os
import shutil
import uuid
import zipfile
from pathlib import Path
from django.db import transaction
from django.conf import settings
from .models import (
    PendingFirmware,
    OfficialFirmware,
    EngineeringFirmware,
    ReadbackFirmware,
    ModifiedFirmware,
    OtherFirmware,
    UnclassifiedFirmware,
    Brand,
    Model,
    Variant,
)
from .crypto import encrypt_password, decrypt_password
from .ai_client import AIClient

ai_client = AIClient()

MAX_UPLOAD_BYTES = getattr(settings, "FIRMWARE_MAX_UPLOAD_BYTES", 100 * 1024 * 1024)  # 100 MB default
ZIP_MAX_MEMBERS = getattr(settings, "FIRMWARE_ZIP_MAX_MEMBERS", 200)
ZIP_MAX_TOTAL_BYTES = getattr(settings, "FIRMWARE_ZIP_MAX_TOTAL_BYTES", 500 * 1024 * 1024)  # 500 MB default
AI_SEND_PASSWORD = getattr(settings, "FIRMWARE_AI_SEND_PASSWORD", False)


def calc_storage_path(brand_slug, model_slug, variant_slug, category, fw_id):
    base = Path(getattr(settings, "FIRMWARE_STORAGE_ROOT", settings.BASE_DIR / "storage"))
    return base / brand_slug / model_slug / variant_slug / category / str(fw_id)


def _safe_filename(name: str) -> str:
    # Prevent path traversal and control length
    return Path(name).name[:255]


def handle_upload(*, uploader, uploaded_brand, uploaded_model, uploaded_variant, file_obj, is_password_protected, password, extra_info=None):
    """
    Handle firmware file upload with comprehensive security validation.
    
    Args:
        uploader: User uploading the file
        uploaded_brand: Brand foreign key
        uploaded_model: Model foreign key
        uploaded_variant: Variant foreign key
        file_obj: Uploaded file object
        is_password_protected: Boolean indicating if file is password protected
        password: Password for protected files
        extra_info: Optional additional metadata
    
    Returns:
        PendingFirmware: Created pending firmware object
    
    Raises:
        ValueError: If file validation fails
    """
    # Critical: Check if file size is None (could indicate upload issues)
    size = getattr(file_obj, "size", None)
    if size is None:
        raise ValueError("File size could not be determined. Upload may have failed.")
    
    # Guard against oversized uploads to prevent resource exhaustion
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(f"Upload exceeds maximum allowed size of {MAX_UPLOAD_BYTES} bytes ({size} bytes provided)")
    
    # Validate minimum file size (avoid empty or corrupted uploads)
    if size < 100:  # 100 bytes minimum
        raise ValueError("File is too small to be a valid firmware (minimum 100 bytes)")
    
    # Validate file mime type using python-magic if available
    # Note: MIME type detection based on file headers can be spoofed.
    # For critical security, combine with extension validation and deeper content analysis.
    try:
        import magic
        mime = magic.Magic(mime=True)
        
        # Read a small chunk to detect mime type
        file_obj.seek(0)
        file_header = file_obj.read(8192)
        file_obj.seek(0)
        
        detected_mime = mime.from_buffer(file_header)
        
        # Allowed mime types for firmware files
        allowed_mimes = {
            'application/zip',
            'application/x-zip-compressed',
            'application/octet-stream',
            'application/x-tar',
            'application/gzip',
            'application/x-gzip',
            'application/x-7z-compressed',
            'application/x-rar-compressed',
        }
        
        if detected_mime not in allowed_mimes:
            raise ValueError(
                f"Invalid file type detected: {detected_mime}. "
                f"Only compressed firmware files are allowed."
            )
            
        # Additional validation: check file extension as secondary confirmation
        file_extension = Path(file_obj.name).suffix.lower()
        allowed_extensions = {'.zip', '.tar', '.gz', '.tgz', '.7z', '.rar', '.bin', '.img'}
        
        # Require a valid extension explicitly
        if not file_extension:
            raise ValueError("File must have a valid extension (e.g., .zip, .tar, .gz)")
        
        if file_extension not in allowed_extensions:
            raise ValueError(
                f"Invalid file extension: {file_extension}. "
                f"Only firmware archive files are allowed: {', '.join(sorted(allowed_extensions))}"
            )
    except ImportError:
        # python-magic not installed - skip mime validation but log warning
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("python-magic not installed. Skipping MIME type validation. Install with: pip install python-magic")
    except Exception as exc:
        # Log but don't fail on mime detection errors
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("MIME type detection failed: %s", exc)
    
    # TODO: Add virus scanning integration point
    # if ENABLE_VIRUS_SCAN:
    #     scan_result = virus_scanner.scan_file(file_obj)
    #     if not scan_result.is_clean:
    #         raise ValueError(f"File failed virus scan: {scan_result.threat_name}")

    tmp_root = Path(getattr(settings, "FIRMWARE_STORAGE_ROOT", settings.BASE_DIR / "storage"))
    tmp_dir = tmp_root / "pending" / str(uuid.uuid4())
    tmp_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(file_obj.name)
    file_path = tmp_dir / safe_name
    with open(file_path, "wb") as f:
        for chunk in file_obj.chunks():
            f.write(chunk)

    pw_token = encrypt_password(password) if (is_password_protected and password) else ""
    return PendingFirmware.objects.create(
        original_file_name=safe_name,
        stored_file_path=str(file_path),
        uploader=uploader,
        uploaded_brand=uploaded_brand,
        uploaded_model=uploaded_model,
        uploaded_variant=uploaded_variant,
        is_password_protected=is_password_protected,
        encrypted_password=pw_token,
        metadata={"extra_info": extra_info} if extra_info else {},
    )


def attempt_extraction(pf: PendingFirmware) -> None:
    if not pf.is_password_protected:
        pf.extraction_status = "success"
        pf.save(update_fields=["extraction_status"])
        return
    try:
        password = pf.encrypted_password and decrypt_password(pf.encrypted_password)
    except Exception:
        pf.password_validation_status = "invalid"
        pf.extraction_status = "failed"
        pf.save(update_fields=["password_validation_status", "extraction_status"])
        return
    try:
        if zipfile.is_zipfile(pf.stored_file_path):
            dest_dir = Path(pf.stored_file_path).parent
            with zipfile.ZipFile(pf.stored_file_path) as zf:
                total_bytes = 0
                member_count = 0
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    member_count += 1
                    if member_count > ZIP_MAX_MEMBERS:
                        raise ValueError("Archive has too many entries")
                    total_bytes += member.file_size
                    if total_bytes > ZIP_MAX_TOTAL_BYTES or member.file_size > ZIP_MAX_TOTAL_BYTES:
                        raise ValueError("Archive exceeds allowed uncompressed size")
                    target_path = dest_dir / member.filename
                    # Prevent path traversal
                    if not str(target_path.resolve()).startswith(str(dest_dir.resolve())):
                        continue
                    zf.extract(member, dest_dir, pwd=password.encode())
            pf.password_validation_status = "valid"
            pf.extraction_status = "success"
        else:
            pf.password_validation_status = "unknown"
            pf.extraction_status = "pending"
    except Exception:
        pf.password_validation_status = "invalid"
        pf.extraction_status = "failed"
    pf.save(update_fields=["password_validation_status", "extraction_status"])


def run_ai_analysis(pf: PendingFirmware) -> None:
    """
    Run AI analysis on pending firmware with proper error handling and retries.
    
    Args:
        pf: PendingFirmware instance to analyze
    
    Implements:
        - Specific exception handling (AiClientError, Timeout)
        - Exponential backoff retry logic
        - Detailed error logging
    """
    import time
    import random
    import logging
    from apps.core.ai_client import AiClientError
    
    logger = logging.getLogger(__name__)
    pw = decrypt_password(pf.encrypted_password) if (AI_SEND_PASSWORD and pf.encrypted_password) else None
    
    # Retry configuration
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    JITTER_FACTOR = 0.1  # 10% jitter
    MAX_DELAY = 30.0  # seconds
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = ai_client.analyze_firmware(pf.stored_file_path, password=pw)
            
            # Successfully got result
            pf.ai_brand = result.get("brand", "") or ""
            pf.ai_model = result.get("model", "") or ""
            pf.ai_variant = result.get("variant", "") or ""
            pf.ai_category = result.get("category") or None
            pf.ai_subtype = result.get("subtype") or None
            pf.chipset = result.get("chipset", "") or ""
            pf.partitions = result.get("partitions", []) or []
            pf.metadata = {**pf.metadata, **(result.get("metadata") or {})}
            pf.save()
            return  # Success - exit
            
        except AiClientError as exc:
            # AI client specific error
            error_msg = f"AI client error on attempt {attempt}/{MAX_RETRIES}: {exc}"
            logger.error(error_msg, exc_info=True)
            
            if attempt >= MAX_RETRIES:
                # Final attempt failed
                pf.metadata = {
                    **pf.metadata, 
                    "ai_error": "ai_client_error",
                    "ai_error_detail": str(exc),
                    "ai_attempts": attempt
                }
                pf.save(update_fields=["metadata"])
                return
                
        except TimeoutError as exc:
            # Timeout error
            error_msg = f"AI analysis timeout on attempt {attempt}/{MAX_RETRIES}: {exc}"
            logger.error(error_msg, exc_info=True)
            
            if attempt >= MAX_RETRIES:
                pf.metadata = {
                    **pf.metadata,
                    "ai_error": "analysis_timeout",
                    "ai_error_detail": "AI analysis took too long to complete",
                    "ai_attempts": attempt
                }
                pf.save(update_fields=["metadata"])
                return
                
        except Exception as exc:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error during AI analysis on attempt {attempt}/{MAX_RETRIES}: {exc}"
            logger.exception(error_msg)
            
            if attempt >= MAX_RETRIES:
                pf.metadata = {
                    **pf.metadata,
                    "ai_error": "analysis_failed",
                    "ai_error_detail": str(exc),
                    "ai_error_type": type(exc).__name__,
                    "ai_attempts": attempt
                }
                pf.save(update_fields=["metadata"])
                return
        
        # Calculate exponential backoff with proper random jitter
        if attempt < MAX_RETRIES:
            delay = BASE_DELAY * (2 ** (attempt - 1))
            jitter = delay * JITTER_FACTOR * random.random()
            sleep_time = min(delay + jitter, MAX_DELAY)
            logger.info(f"Retrying AI analysis after {sleep_time:.2f}s (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(sleep_time)


@transaction.atomic
def moderate_and_route(
    pf: PendingFirmware,
    decision: str,
    *,
    admin_user,
    category: str | None = None,
    subtype: str | None = None,
    brand: Brand | None = None,
    model: Model | None = None,
    variant: Variant | None = None,
    notes: str = "",
    unclassified_reason: str = "",
):
    pf.admin_decision = decision
    pf.admin_notes = notes
    if decision == "rejected":
        pf.save(update_fields=["admin_decision", "admin_notes"])
        return None

    target_brand = brand or pf.uploaded_brand
    target_model = model or pf.uploaded_model
    target_variant = variant or pf.uploaded_variant
    final_cat = category or pf.ai_category or "unclassified"

    base_kwargs = dict(
        original_file_name=pf.original_file_name,
        stored_file_path="",
        uploader=pf.uploader,
        brand=target_brand,
        model=target_model,
        variant=target_variant,
        chipset=pf.chipset,
        partitions=pf.partitions,
        is_password_protected=pf.is_password_protected,
        encrypted_password=pf.encrypted_password,
        metadata=pf.metadata,
    )

    brand_slug = (target_brand.slug if target_brand else "unknown")
    model_slug = (target_model.slug if target_model else "unknown")
    variant_slug = (target_variant.slug if target_variant else "unknown")
    target_dir = calc_storage_path(brand_slug, model_slug, variant_slug, final_cat, pf.id)
    os.makedirs(target_dir, exist_ok=True)
    final_path = Path(target_dir) / _safe_filename(pf.original_file_name)
    shutil.move(pf.stored_file_path, final_path)
    base_kwargs["stored_file_path"] = str(final_path)

    if final_cat == "official":
        rec = OfficialFirmware.objects.create(**base_kwargs)
    elif final_cat == "engineering":
        rec = EngineeringFirmware.objects.create(**base_kwargs, subtype=subtype or "")
    elif final_cat == "readback":
        rec = ReadbackFirmware.objects.create(**base_kwargs)
    elif final_cat == "modified":
        rec = ModifiedFirmware.objects.create(**base_kwargs, subtype=subtype or "")
    elif final_cat == "other":
        rec = OtherFirmware.objects.create(**base_kwargs, subtype=subtype or "")
    else:
        rec = UnclassifiedFirmware.objects.create(**base_kwargs, reason=unclassified_reason or "unclassified")

    pf.category_locked = True
    pf.admin_decision = "approved"
    pf.save(update_fields=["category_locked", "admin_decision", "admin_notes"])
    return rec
