"""
Cloud Storage Provisioning Service

Handles automatic provisioning of service accounts and credentials for cloud storage providers.
Supports Google Drive/Shared Drive, OneDrive, Dropbox, MEGA, and other providers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class CloudStorageProvisioner:
    """
    Provisions and manages cloud storage accounts and service accounts.
    Auto-creates JSON credential files and configures access.
    """

    CREDENTIALS_DIR = "storage_credentials"
    SERVICE_ACCOUNTS_DIR = "service_accounts"

    def __init__(self):
        self.base_path = Path(settings.BASE_DIR) / self.CREDENTIALS_DIR
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.sa_path = self.base_path / self.SERVICE_ACCOUNTS_DIR
        self.sa_path.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # GOOGLE DRIVE / SHARED DRIVE PROVISIONING
    # =========================================================================

    def provision_google_service_account(
        self, provider, service_account_info: dict[str, Any], account_name: str = None
    ) -> dict[str, Any]:
        """
        Create service account JSON file from provided credentials.

        Args:
            provider: CloudStorageProvider instance
            service_account_info: Service account JSON data (from Google Cloud Console)
            account_name: Optional custom name for the service account

        Returns:
            Dict with service_account info including file path
        """
        from ..models import ServiceAccount

        try:
            # Validate required fields
            required_fields = ["type", "project_id", "private_key", "client_email"]
            for field in required_fields:
                if field not in service_account_info:
                    raise ValueError(f"Missing required field: {field}")

            if service_account_info.get("type") != "service_account":
                raise ValueError("Invalid credential type - must be 'service_account'")

            # Generate unique filename
            email = service_account_info["client_email"]
            email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
            filename = f"sa_{provider.id}_{email_hash}.json"
            filepath = self.sa_path / filename

            # Write JSON file
            with open(filepath, "w") as f:
                json.dump(service_account_info, f, indent=2)

            # Set restricted permissions (owner read only)
            os.chmod(filepath, 0o600)

            # Create or update ServiceAccount record
            sa_name = account_name or f"SA_{email.split('@')[0]}"

            # Find associated shared drive
            shared_drive = provider.shared_drives.first()

            if shared_drive:
                sa, created = ServiceAccount.objects.update_or_create(
                    email=email,
                    defaults={
                        "shared_drive": shared_drive,
                        "name": sa_name,
                        "credentials_path": str(filepath),
                        "is_active": True,
                        "quota_reset_at": timezone.now() + timedelta(days=1),
                    },
                )

                logger.info(
                    f"{'Created' if created else 'Updated'} service account: {email}"
                )

                return {
                    "success": True,
                    "service_account_id": str(sa.id),
                    "email": email,
                    "name": sa_name,
                    "credentials_path": str(filepath),
                    "created": created,
                }

            return {
                "success": True,
                "email": email,
                "name": sa_name,
                "credentials_path": str(filepath),
                "message": "Service account file created. Link to SharedDrive manually.",
            }

        except Exception as e:
            logger.error(f"Failed to provision service account: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def bulk_provision_google_service_accounts(
        self, provider, service_accounts_json: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Bulk provision multiple service accounts from JSON array.

        Args:
            provider: CloudStorageProvider instance
            service_accounts_json: List of service account JSON objects

        Returns:
            Summary of provisioning results
        """
        results = {
            "total": len(service_accounts_json),
            "success": 0,
            "failed": 0,
            "accounts": [],
            "errors": [],
        }

        for idx, sa_info in enumerate(service_accounts_json):
            result = self.provision_google_service_account(
                provider=provider,
                service_account_info=sa_info,
                account_name=f"SA_{idx + 1:03d}",
            )

            if result.get("success"):
                results["success"] += 1
                results["accounts"].append(result)
            else:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "index": idx,
                        "error": result.get("error"),
                    }
                )

        logger.info(
            f"Bulk provisioned {results['success']}/{results['total']} service accounts"
        )

        return results

    def fetch_google_shared_drives(self, provider) -> list[dict[str, Any]]:
        """
        Fetch all shared drives accessible by the provider's credentials.

        Args:
            provider: CloudStorageProvider instance with valid credentials

        Returns:
            List of shared drive info dicts
        """
        from ..models import SharedDriveAccount

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            # Get credentials
            creds_path = provider.service_account_json_path
            if not creds_path or not os.path.exists(creds_path):
                # Try to use stored credentials
                creds_data = provider.get_credentials()
                if not creds_data:
                    raise ValueError("No valid credentials found")

                # Create temp credentials file
                creds_path = self.sa_path / f"temp_{provider.id}.json"
                with open(creds_path, "w") as f:
                    json.dump(creds_data, f)

            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=["https://www.googleapis.com/auth/drive"]
            )
            service = build("drive", "v3", credentials=credentials)

            # List all shared drives
            drives = []
            page_token = None

            while True:
                response = (
                    service.drives()
                    .list(
                        pageSize=100,
                        pageToken=page_token,
                        fields="nextPageToken, drives(id, name, capabilities, createdTime)",
                    )
                    .execute()
                )

                drives.extend(response.get("drives", []))
                page_token = response.get("nextPageToken")

                if not page_token:
                    break

            # Create/update SharedDriveAccount records
            created_drives = []
            for drive in drives:
                sda, created = SharedDriveAccount.objects.update_or_create(
                    drive_id=drive["id"],
                    defaults={
                        "provider": provider,
                        "name": drive["name"],
                        "owner_email": provider.account_email,
                        "is_active": True,
                    },
                )
                created_drives.append(
                    {
                        "id": str(sda.id),
                        "drive_id": drive["id"],
                        "name": drive["name"],
                        "created": created,
                    }
                )

            logger.info(
                f"Found {len(drives)} shared drives for provider {provider.name}"
            )

            return created_drives

        except Exception as e:
            logger.error(f"Failed to fetch shared drives: {e}")
            return []

    def setup_google_drive_from_oauth(
        self,
        provider,
        oauth_code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """
        Complete OAuth2 flow and setup Google Drive access.

        Args:
            provider: CloudStorageProvider instance
            oauth_code: Authorization code from OAuth consent
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI

        Returns:
            Setup result with tokens
        """
        try:
            from google_auth_oauthlib.flow import Flow

            # Create flow from client config
            client_config = {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            }

            flow = Flow.from_client_config(
                client_config,
                scopes=["https://www.googleapis.com/auth/drive"],
                redirect_uri=redirect_uri,
            )

            # Exchange code for tokens
            flow.fetch_token(code=oauth_code)
            credentials = flow.credentials

            # Store tokens
            provider.set_access_token(credentials.token)
            if credentials.refresh_token:
                provider.set_refresh_token(credentials.refresh_token)
            provider.token_expiry = credentials.expiry

            # Store full credentials for service use
            provider.set_credentials(
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": credentials.refresh_token,
                }
            )

            provider.status = "active"
            provider.auth_type = "oauth2"
            provider.save()

            logger.info(f"Successfully configured OAuth for provider {provider.name}")

            return {
                "success": True,
                "provider_id": str(provider.id),
                "status": provider.status,
            }

        except Exception as e:
            logger.error(f"OAuth setup failed: {e}")
            provider.status = "error"
            provider.last_error = str(e)
            provider.save()
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # ONEDRIVE / SHAREPOINT PROVISIONING
    # =========================================================================

    def provision_onedrive(
        self,
        provider,
        client_id: str,
        client_secret: str,
        tenant_id: str = "common",
        site_id: str = None,
    ) -> dict[str, Any]:
        """
        Setup OneDrive/SharePoint access with app credentials.

        Args:
            provider: CloudStorageProvider instance
            client_id: Azure AD application client ID
            client_secret: Azure AD application client secret
            tenant_id: Azure tenant ID (default: 'common' for multi-tenant)
            site_id: SharePoint site ID (optional)

        Returns:
            Setup result
        """
        try:
            # Store credentials
            provider.set_credentials(
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "tenant_id": tenant_id,
                    "site_id": site_id,
                }
            )

            provider.account_id = tenant_id
            provider.auth_type = "oauth2"
            provider.status = "configuring"
            provider.save()

            # Generate OAuth URL for authorization
            auth_url = (
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
                f"?client_id={client_id}"
                f"&response_type=code"
                f"&scope=https://graph.microsoft.com/Files.ReadWrite.All offline_access"
            )

            logger.info(f"OneDrive provider configured: {provider.name}")

            return {
                "success": True,
                "provider_id": str(provider.id),
                "auth_url": auth_url,
                "status": "configuring",
                "message": "Complete OAuth authorization using the auth_url",
            }

        except Exception as e:
            logger.error(f"OneDrive setup failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # DROPBOX PROVISIONING
    # =========================================================================

    def provision_dropbox(
        self,
        provider,
        app_key: str,
        app_secret: str,
        access_token: str = None,
        refresh_token: str = None,
    ) -> dict[str, Any]:
        """
        Setup Dropbox access with app credentials.

        Args:
            provider: CloudStorageProvider instance
            app_key: Dropbox app key
            app_secret: Dropbox app secret
            access_token: Pre-existing access token (optional)
            refresh_token: Pre-existing refresh token (optional)

        Returns:
            Setup result
        """
        try:
            provider.set_credentials(
                {
                    "app_key": app_key,
                    "app_secret": app_secret,
                }
            )

            if access_token:
                provider.set_access_token(access_token)
            if refresh_token:
                provider.set_refresh_token(refresh_token)

            provider.auth_type = "oauth2"
            provider.status = "active" if access_token else "configuring"
            provider.save()

            # Generate OAuth URL if no tokens
            auth_url = None
            if not access_token:
                auth_url = (
                    f"https://www.dropbox.com/oauth2/authorize"
                    f"?client_id={app_key}"
                    f"&response_type=code"
                    f"&token_access_type=offline"
                )

            logger.info(f"Dropbox provider configured: {provider.name}")

            return {
                "success": True,
                "provider_id": str(provider.id),
                "auth_url": auth_url,
                "status": provider.status,
            }

        except Exception as e:
            logger.error(f"Dropbox setup failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # MEGA PROVISIONING
    # =========================================================================

    def provision_mega(self, provider, email: str, password: str) -> dict[str, Any]:
        """
        Setup MEGA access with username/password.

        Args:
            provider: CloudStorageProvider instance
            email: MEGA account email
            password: MEGA account password

        Returns:
            Setup result
        """
        try:
            provider.set_credentials(
                {
                    "email": email,
                    "password": password,
                }
            )

            provider.account_email = email
            provider.auth_type = "username_password"
            provider.status = "active"
            provider.save()

            logger.info(f"MEGA provider configured: {provider.name}")

            return {
                "success": True,
                "provider_id": str(provider.id),
                "status": "active",
            }

        except Exception as e:
            logger.error(f"MEGA setup failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # S3-COMPATIBLE STORAGE PROVISIONING
    # =========================================================================

    def provision_s3_compatible(
        self,
        provider,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str = "us-east-1",
        endpoint_url: str = None,
    ) -> dict[str, Any]:
        """
        Setup S3-compatible storage (AWS S3, Wasabi, Backblaze B2, etc.)

        Args:
            provider: CloudStorageProvider instance
            access_key_id: S3 access key ID
            secret_access_key: S3 secret access key
            bucket_name: Target bucket name
            region: AWS region
            endpoint_url: Custom endpoint for non-AWS S3 (Wasabi, B2, etc.)

        Returns:
            Setup result
        """
        try:
            provider.set_credentials(
                {
                    "access_key_id": access_key_id,
                    "secret_access_key": secret_access_key,
                }
            )

            provider.bucket_name = bucket_name
            provider.region = region
            if endpoint_url:
                provider.endpoint_url = endpoint_url

            provider.auth_type = "api_key"
            provider.status = "active"
            provider.save()

            logger.info(f"S3-compatible provider configured: {provider.name}")

            return {
                "success": True,
                "provider_id": str(provider.id),
                "bucket": bucket_name,
                "region": region,
                "status": "active",
            }

        except Exception as e:
            logger.error(f"S3 setup failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def validate_provider_connection(self, provider) -> dict[str, Any]:
        """
        Test connection to cloud storage provider.

        Args:
            provider: CloudStorageProvider instance

        Returns:
            Validation result with quota info
        """
        try:
            if provider.provider in ("google_drive", "google_shared_drive"):
                return self._validate_google_drive(provider)
            elif provider.provider == "onedrive":
                return self._validate_onedrive(provider)
            elif provider.provider == "dropbox":
                return self._validate_dropbox(provider)
            elif provider.provider in ("s3", "wasabi", "backblaze"):
                return self._validate_s3(provider)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported provider: {provider.provider}",
                }

        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _validate_google_drive(self, provider) -> dict[str, Any]:
        """Validate Google Drive connection."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds_path = provider.service_account_json_path
            if not creds_path or not os.path.exists(creds_path):
                creds_data = provider.get_credentials()
                if not creds_data:
                    raise ValueError("No credentials configured")
                creds_path = self.sa_path / f"temp_{provider.id}.json"
                with open(creds_path, "w") as f:
                    json.dump(creds_data, f)

            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=["https://www.googleapis.com/auth/drive"]
            )
            service = build("drive", "v3", credentials=credentials)

            # Get storage quota
            about = service.about().get(fields="storageQuota, user").execute()
            quota = about.get("storageQuota", {})
            user = about.get("user", {})

            # Update provider with quota info
            provider.total_space_bytes = int(quota.get("limit", 0))
            provider.used_space_bytes = int(quota.get("usage", 0))
            provider.account_email = user.get("emailAddress", "")
            provider.status = "active"
            provider.last_sync_at = timezone.now()
            provider.last_error = ""
            provider.save()

            return {
                "success": True,
                "provider": provider.provider,
                "email": provider.account_email,
                "total_space_gb": provider.total_space_bytes / (1024**3),
                "used_space_gb": provider.used_space_bytes / (1024**3),
                "available_space_gb": provider.available_space_gb(),
            }

        except Exception as e:
            provider.status = "error"
            provider.last_error = str(e)
            provider.save()
            raise

    def _validate_onedrive(self, provider) -> dict[str, Any]:
        """Validate OneDrive connection."""
        # Placeholder - implement with Microsoft Graph API
        return {"success": True, "message": "OneDrive validation not yet implemented"}

    def _validate_dropbox(self, provider) -> dict[str, Any]:
        """Validate Dropbox connection."""
        # Placeholder - implement with Dropbox API
        return {"success": True, "message": "Dropbox validation not yet implemented"}

    def _validate_s3(self, provider) -> dict[str, Any]:
        """Validate S3-compatible storage connection."""
        try:
            import boto3
            from botocore.config import Config

            creds = provider.get_credentials()

            config = Config(
                region_name=provider.region or "us-east-1", signature_version="s3v4"
            )

            client = boto3.client(
                "s3",
                aws_access_key_id=creds.get("access_key_id"),
                aws_secret_access_key=creds.get("secret_access_key"),
                endpoint_url=provider.endpoint_url or None,
                config=config,
            )

            # Test connection by listing buckets
            client.head_bucket(Bucket=provider.bucket_name)

            provider.status = "active"
            provider.last_sync_at = timezone.now()
            provider.last_error = ""
            provider.save()

            return {
                "success": True,
                "provider": provider.provider,
                "bucket": provider.bucket_name,
                "region": provider.region,
            }

        except Exception as e:
            provider.status = "error"
            provider.last_error = str(e)
            provider.save()
            raise

    def sync_all_service_accounts(self, provider) -> dict[str, Any]:
        """
        Sync all service accounts for a provider.
        Re-scans credentials directory and updates database records.

        Args:
            provider: CloudStorageProvider instance

        Returns:
            Sync result summary
        """
        from ..models import ServiceAccount

        results = {
            "scanned": 0,
            "created": 0,
            "updated": 0,
            "errors": [],
        }

        # Find all JSON files for this provider
        pattern = f"sa_{provider.id}_*.json"

        for filepath in self.sa_path.glob(pattern):
            results["scanned"] += 1

            try:
                with open(filepath) as f:
                    sa_data = json.load(f)

                email = sa_data.get("client_email")
                if not email:
                    continue

                shared_drive = provider.shared_drives.first()
                if not shared_drive:
                    continue

                sa, created = ServiceAccount.objects.update_or_create(
                    email=email,
                    defaults={
                        "shared_drive": shared_drive,
                        "name": f"SA_{email.split('@')[0]}",
                        "credentials_path": str(filepath),
                        "is_active": True,
                        "quota_reset_at": timezone.now() + timedelta(days=1),
                    },
                )

                if created:
                    results["created"] += 1
                else:
                    results["updated"] += 1

            except Exception as e:
                results["errors"].append(
                    {
                        "file": str(filepath),
                        "error": str(e),
                    }
                )

        logger.info(f"Synced service accounts: {results}")
        return results

    def export_service_accounts_zip(self, provider) -> bytes:
        """
        Export all service account JSON files as a ZIP archive.

        Args:
            provider: CloudStorageProvider instance

        Returns:
            ZIP file bytes
        """
        import io
        import zipfile

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            pattern = f"sa_{provider.id}_*.json"
            for filepath in self.sa_path.glob(pattern):
                zf.write(filepath, filepath.name)

        buffer.seek(0)
        return buffer.read()


# Singleton instance
provisioner = CloudStorageProvisioner()
