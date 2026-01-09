# Example: Firmware App Integration with Storage
"""
This file demonstrates how to integrate storage functionality into firmware app
while maintaining complete modularity and loose coupling.

IMPORTANT: This is a REFERENCE EXAMPLE only. Do not import this file directly.
Copy the patterns shown here into your firmware app views/admin/services.
"""

# ============================================================================
# EXAMPLE 1: Upload firmware file from firmware view
# ============================================================================
# File: apps/firmware/views.py or apps/firmware/api.py

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@staff_member_required
@require_POST
def upload_firmware_file(request, firmware_id):
    """Upload firmware file to cloud storage"""
    from django.apps import apps

    # Get firmware object (no direct import)
    Firmware = apps.get_model("firmware", "Firmware")
    firmware = Firmware.objects.get(id=firmware_id)

    # Check if storage app is available
    if not apps.is_installed("apps.storage"):
        return JsonResponse(
            {"success": False, "error": "Storage app not installed"}, status=503
        )

    # Use helper to upload
    from apps.storage.helpers import FirmwareStorageHelper

    # Assume file uploaded via request.FILES
    uploaded_file = request.FILES.get("firmware_file")
    if not uploaded_file:
        return JsonResponse({"success": False, "error": "No file uploaded"})

    # Save temporarily
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
        for chunk in uploaded_file.chunks():
            tmp_file.write(chunk)
        tmp_path = tmp_file.name

    try:
        # Upload to cloud storage
        storage_location = FirmwareStorageHelper.upload_firmware(
            firmware_object=firmware,
            local_path=tmp_path,
            brand_name=firmware.brand.name,  # Adjust based on your model
            model_name=firmware.model.name,
            variant_name=firmware.variant,
            category="firmware",
        )

        if storage_location:
            return JsonResponse(
                {
                    "success": True,
                    "storage_id": str(storage_location.id),
                    "storage_type": storage_location.storage_type,
                    "message": "File uploaded successfully",
                }
            )
        else:
            return JsonResponse({"success": False, "error": "Upload failed"})
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================================
# EXAMPLE 2: Request firmware download from firmware view
# ============================================================================
# File: apps/firmware/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def download_firmware(request, firmware_id):
    """Initiate firmware download for user"""
    from django.apps import apps

    Firmware = apps.get_model("firmware", "Firmware")
    firmware = Firmware.objects.get(id=firmware_id)

    # Check if storage app is available
    if not apps.is_installed("apps.storage"):
        # Fallback to direct download or external links
        return redirect(firmware.direct_download_url)

    # Use helper to request download
    from apps.storage.helpers import FirmwareStorageHelper

    session = FirmwareStorageHelper.request_download(
        user=request.user, firmware_object=firmware
    )

    if session:
        # Redirect to download status page
        return redirect("firmware:download_status", session_id=session.id)
    else:
        # Fallback to external link
        locations = FirmwareStorageHelper.get_storage_locations(firmware)
        external_links = [
            loc for loc in locations if loc.storage_type == "external_link"
        ]
        if external_links:
            return redirect(external_links[0].external_link_url)

        return JsonResponse({"error": "No download available"}, status=404)


# ============================================================================
# EXAMPLE 3: Check download status (AJAX endpoint)
# ============================================================================
# File: apps/firmware/views.py


@login_required
def download_status(request, session_id):
    """Check download session status"""
    from apps.storage.helpers import FirmwareStorageHelper

    status = FirmwareStorageHelper.get_download_status(session_id)

    if status["status"] == "ready":
        # Download is ready
        return JsonResponse(
            {
                "ready": True,
                "download_url": status["download_url"],
                "expires_at": status["expires_at"].isoformat(),
                "time_remaining_seconds": status["time_remaining"],
            }
        )
    elif status["status"] == "copying":
        return JsonResponse(
            {
                "ready": False,
                "status": "preparing",
                "message": "Preparing your download...",
            }
        )
    else:
        return JsonResponse(
            {
                "ready": False,
                "status": status["status"],
                "error": status.get("error", "Unknown error"),
            }
        )


# ============================================================================
# EXAMPLE 4: Add external link from firmware admin
# ============================================================================
# File: apps/firmware/admin.py

from django.contrib import admin, messages
from django.shortcuts import render
from django.urls import path


class FirmwareAdmin(admin.ModelAdmin):
    # ... existing admin config ...

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/add-external-link/",
                self.admin_site.admin_view(self.add_external_link_view),
                name="firmware_add_external_link",
            ),
        ]
        return custom_urls + urls

    def add_external_link_view(self, request, object_id):
        """Admin view to add external download link"""
        from django.apps import apps

        Firmware = apps.get_model("firmware", "Firmware")
        firmware = Firmware.objects.get(id=object_id)

        if request.method == "POST":
            provider = request.POST.get("provider")
            url = request.POST.get("url")
            password = request.POST.get("password", "")
            notes = request.POST.get("notes", "")

            # Check if storage app is available
            if apps.is_installed("apps.storage"):
                from apps.storage.helpers import FirmwareStorageHelper

                location = FirmwareStorageHelper.add_external_link(
                    firmware_object=firmware,
                    provider=provider,
                    url=url,
                    password=password if password else None,
                    notes=notes if notes else None,
                )

                if location:
                    messages.success(request, f"External link added: {provider}")
                else:
                    messages.error(request, "Failed to add external link")
            else:
                messages.warning(request, "Storage app not installed")

            return redirect("admin:firmware_firmware_change", object_id)

        context = {
            "firmware": firmware,
            "title": "Add External Download Link",
            "providers": ["mediafire", "mega", "google_drive", "dropbox", "other"],
        }
        return render(request, "admin/firmware/add_external_link.html", context)


# ============================================================================
# EXAMPLE 5: Check storage quota before upload
# ============================================================================
# File: apps/firmware/services.py


class FirmwareUploadService:
    """Service for uploading firmware files"""

    def can_upload(self) -> bool:
        """Check if storage quota is available"""
        from django.apps import apps

        if not apps.is_installed("apps.storage"):
            return True  # Fallback to other storage method

        from apps.storage.helpers import FirmwareStorageHelper

        quota_info = FirmwareStorageHelper.check_storage_quota()

        if not quota_info["available"]:
            return False

        # Check if any drive has capacity
        for drive in quota_info.get("drives", []):
            if drive["health"] == "healthy" and drive["utilization"] < 90:
                return True

        return False

    def upload_firmware(self, firmware, file_path, brand_name):
        """Upload firmware with quota check"""
        if not self.can_upload():
            raise Exception("Storage quota exceeded")

        from apps.storage.helpers import FirmwareStorageHelper

        return FirmwareStorageHelper.upload_firmware(
            firmware_object=firmware, local_path=file_path, brand_name=brand_name
        )


# ============================================================================
# EXAMPLE 6: Listen to storage signals in firmware app
# ============================================================================
# File: apps/firmware/signal_handlers.py (NEW FILE)

from django.dispatch import receiver

from apps.core.signals import (
    firmware_download_ready,
    firmware_uploaded,
    storage_quota_exhausted,
)


@receiver(firmware_uploaded)
def update_firmware_storage_status(sender, storage_location, **kwargs):
    """Update firmware model when upload completes"""

    # Get firmware object via GenericForeignKey
    firmware = storage_location.content_object

    if firmware:
        # Update firmware model (adjust field names based on your model)
        firmware.is_uploaded = True
        firmware.storage_location = str(storage_location.id)
        firmware.storage_type = storage_location.storage_type
        firmware.save(update_fields=["is_uploaded", "storage_location", "storage_type"])


@receiver(firmware_download_ready)
def log_firmware_download(sender, session, firmware, **kwargs):
    """Log firmware download activity"""
    from django.apps import apps

    # Get download log model (if you have one)
    try:
        FirmwareDownloadLog = apps.get_model("firmware", "FirmwareDownloadLog")
        FirmwareDownloadLog.objects.create(
            firmware=firmware,
            user=session.user,
            session_id=str(session.id),
            download_url=session.download_url,
        )
    except LookupError:
        pass  # Model doesn't exist


@receiver(storage_quota_exhausted)
def alert_admin_quota_exhausted(sender, drive, **kwargs):
    """Send alert when storage quota is exhausted"""
    from django.core.mail import mail_admins

    mail_admins(
        subject=f"Storage Quota Alert: {drive.drive_name}",
        message=f"Shared drive {drive.drive_name} has reached {drive.utilization_percent()}% capacity.",
        fail_silently=True,
    )


# ============================================================================
# EXAMPLE 7: Register signal handlers in firmware app config
# ============================================================================
# File: apps/firmware/apps.py

from django.apps import AppConfig


class FirmwareConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.firmware"
    verbose_name = "Firmware Management"

    def ready(self):
        """Import signal handlers when app is ready"""
        # Import existing firmware signals
        # Import storage integration signal handlers
        # (only if storage app is installed)
        from django.apps import apps

        import apps.firmware.signals

        if apps.is_installed("apps.storage"):
            import apps.firmware.signal_handlers


# ============================================================================
# EXAMPLE 8: Template integration for download button
# ============================================================================
# File: apps/firmware/templates/firmware/detail.html
"""
{% extends "base.html" %}

{% block content %}
<div class="firmware-detail">
    <h1>{{ firmware.name }}</h1>

    <!-- Storage-aware download button -->
    {% if user.is_authenticated %}
        <button id="download-btn"
                data-firmware-id="{{ firmware.id }}"
                class="btn btn-primary">
            Download Firmware
        </button>

        <div id="download-status" style="display:none;">
            <div class="spinner">Preparing download...</div>
            <p id="status-message"></p>
        </div>

        <script>
        document.getElementById('download-btn').addEventListener('click', async function() {
            const firmwareId = this.dataset.firmwareId;
            this.style.display = 'none';
            document.getElementById('download-status').style.display = 'block';

            // Request download
            const response = await fetch(`/api/firmware/${firmwareId}/download/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            const data = await response.json();

            if (data.session_id) {
                // Poll for status
                checkDownloadStatus(data.session_id);
            } else if (data.direct_url) {
                // Direct download available
                window.location.href = data.direct_url;
            }
        });

        async function checkDownloadStatus(sessionId) {
            const response = await fetch(`/api/storage/download/${sessionId}/status/`);
            const status = await response.json();

            if (status.ready) {
                document.getElementById('status-message').innerHTML =
                    `<a href="${status.download_url}" class="btn btn-success">Download Now</a>` +
                    `<p>Link expires in ${Math.floor(status.time_remaining_seconds / 60)} minutes</p>`;
            } else if (status.status === 'copying') {
                document.getElementById('status-message').textContent =
                    'Preparing your download... Please wait.';
                setTimeout(() => checkDownloadStatus(sessionId), 3000);
            } else {
                document.getElementById('status-message').textContent =
                    'Error: ' + (status.error || 'Unknown error');
            }
        }

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        </script>
    {% else %}
        <p>Please <a href="{% url 'account_login' %}">login</a> to download.</p>
    {% endif %}
</div>
{% endblock %}
"""


# ============================================================================
# SUMMARY: Integration Patterns
# ============================================================================
"""
KEY PRINCIPLES:

1. **Always check if storage app is installed**:
   if apps.is_installed('apps.storage'):
       # Use storage features
   else:
       # Fallback to alternative

2. **Use helpers, not direct imports**:
   from apps.storage.helpers import FirmwareStorageHelper
   # NOT: from apps.storage.models import FirmwareStorageLocation

3. **Use lazy model loading**:
   Firmware = apps.get_model('firmware', 'Firmware')
   # NOT: from apps.firmware.models import Firmware

4. **Listen to signals for events**:
   @receiver(firmware_uploaded)
   def handle_upload(sender, storage_location, **kwargs):
       # React to storage events

5. **Provide fallbacks**:
   # Try cloud storage
   location = FirmwareStorageHelper.upload_firmware(...)
   if not location:
       # Fallback to external link
       return firmware.external_download_url

6. **Register signal handlers in apps.py**:
   def ready(self):
       import apps.firmware.signal_handlers

This ensures complete modularity - storage app can be disabled without breaking firmware app.
"""
