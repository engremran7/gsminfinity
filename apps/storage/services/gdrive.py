from __future__ import annotations

import io
import logging
import time
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from ..models import ServiceAccount

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """
    Google Drive API operations for firmware storage
    Handles uploads, downloads, copies, and folder management
    """

    SCOPES = ["https://www.googleapis.com/auth/drive"]
    CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks for resumable uploads

    def __init__(self, service_account_obj: ServiceAccount):
        self.service_account = service_account_obj
        self.shared_drive = service_account_obj.shared_drive
        self.service = self._build_service()

    def _build_service(self):
        """Build Google Drive API client"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account.credentials_path, scopes=self.SCOPES
            )
            return build("drive", "v3", credentials=credentials)
        except Exception as e:
            logger.error(
                f"Failed to build Drive service for {self.service_account.name}: {e}"
            )
            raise

    def upload_to_shared_drive(
        self,
        local_path: str,
        folder_id: str = None,
        file_name: str = None,
        mime_type: str = None,
    ) -> dict:
        """
        Upload firmware file to shared drive

        Args:
            local_path: Path to local file
            folder_id: Parent folder ID (uses drive root if None)
            file_name: Custom file name (uses local filename if None)
            mime_type: MIME type (auto-detected if None)

        Returns:
            dict with file_id, name, size, md5
        """
        start_time = time.time()

        try:
            file_metadata = {
                "name": file_name or Path(local_path).name,
                "parents": [folder_id] if folder_id else [self.shared_drive.drive_id],
                "driveId": self.shared_drive.drive_id,
            }

            media = MediaFileUpload(
                local_path,
                mimetype=mime_type,
                resumable=True,
                chunksize=self.CHUNK_SIZE,
            )

            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True,
                    fields="id, name, size, md5Checksum, createdTime",
                )
                .execute()
            )

            # Calculate transfer stats
            duration = time.time() - start_time
            file_size_bytes = int(file.get("size", 0))
            file_size_gb = file_size_bytes / (1024**3)
            speed_mbps = (
                (file_size_bytes * 8 / duration / 1_000_000) if duration > 0 else 0
            )

            # Update service account stats (will be done by caller)
            result = {
                "file_id": file["id"],
                "name": file["name"],
                "size": file_size_bytes,
                "size_gb": file_size_gb,
                "md5": file.get("md5Checksum"),
                "created_time": file.get("createdTime"),
                "speed_mbps": speed_mbps,
            }

            logger.info(
                f"Uploaded {file['name']} ({file_size_gb:.2f}GB) to {self.shared_drive.name} "
                f"in {duration:.1f}s ({speed_mbps:.1f} Mbps)"
            )

            return result

        except HttpError as e:
            logger.error(f"Upload failed: {e}")
            self.service_account.consecutive_failures += 1
            self.service_account.save(update_fields=["consecutive_failures"])
            raise

    def copy_to_user_drive(
        self, source_file_id: str, user_email: str, file_name: str
    ) -> dict:
        """
        Copy file from shared drive to user's personal drive

        Args:
            source_file_id: Source file ID in shared drive
            user_email: User's email address
            file_name: Name for copied file

        Returns:
            dict with file_id, download_link, size
        """
        start_time = time.time()

        try:
            # Copy file
            file_metadata = {
                "name": f"[GsmInfinity] {file_name}",
                "description": "Temporary firmware download. Link expires in 24 hours.",
            }

            copied_file = (
                self.service.files()
                .copy(
                    fileId=source_file_id,
                    body=file_metadata,
                    supportsAllDrives=True,
                    fields="id, name, size, webViewLink, webContentLink",
                )
                .execute()
            )

            # Share with user
            permission = {"type": "user", "role": "reader", "emailAddress": user_email}

            self.service.permissions().create(
                fileId=copied_file["id"],
                body=permission,
                sendNotificationEmail=False,
                supportsAllDrives=True,
            ).execute()

            # Get download link
            link_file = (
                self.service.files()
                .get(
                    fileId=copied_file["id"],
                    fields="webContentLink",
                    supportsAllDrives=True,
                )
                .execute()
            )

            # Calculate stats
            duration = time.time() - start_time
            file_size_bytes = int(copied_file.get("size", 0))
            file_size_gb = file_size_bytes / (1024**3)

            result = {
                "file_id": copied_file["id"],
                "download_link": link_file.get("webContentLink"),
                "view_link": copied_file.get("webViewLink"),
                "size": file_size_bytes,
                "size_gb": file_size_gb,
            }

            logger.info(f"Copied {file_name} to user {user_email} in {duration:.1f}s")

            return result

        except HttpError as e:
            logger.error(f"Copy to user drive failed: {e}")
            self.service_account.consecutive_failures += 1
            self.service_account.save(update_fields=["consecutive_failures"])
            raise

    def delete_file(self, file_id: str) -> bool:
        """
        Delete file from drive

        Args:
            file_id: File ID to delete

        Returns:
            True if successful
        """
        try:
            self.service.files().delete(
                fileId=file_id, supportsAllDrives=True
            ).execute()

            logger.info(f"Deleted file {file_id}")
            return True

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File {file_id} not found (already deleted?)")
                return True

            logger.error(f"Delete failed for {file_id}: {e}")
            raise

    def get_file_info(self, file_id: str) -> dict | None:
        """
        Get file metadata

        Args:
            file_id: File ID

        Returns:
            dict with file info or None if not found
        """
        try:
            file = (
                self.service.files()
                .get(
                    fileId=file_id,
                    fields="id, name, size, md5Checksum, createdTime, modifiedTime, parents",
                    supportsAllDrives=True,
                )
                .execute()
            )

            return file

        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"File {file_id} not found")
                return None

            logger.error(f"Get file info failed for {file_id}: {e}")
            raise

    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> str:
        """
        Create folder in shared drive

        Args:
            folder_name: Name of folder
            parent_folder_id: Parent folder ID (uses drive root if None)

        Returns:
            Folder ID
        """
        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id]
                if parent_folder_id
                else [self.shared_drive.drive_id],
                "driveId": self.shared_drive.drive_id,
            }

            folder = (
                self.service.files()
                .create(body=file_metadata, supportsAllDrives=True, fields="id, name")
                .execute()
            )

            logger.info(f"Created folder '{folder_name}' in {self.shared_drive.name}")
            return folder["id"]

        except HttpError as e:
            logger.error(f"Create folder failed: {e}")
            raise

    def list_files_in_folder(self, folder_id: str, page_size: int = 100) -> list[dict]:
        """
        List files in a folder

        Args:
            folder_id: Folder ID
            page_size: Number of results per page

        Returns:
            List of file dicts
        """
        try:
            query = f"'{folder_id}' in parents and trashed = false"

            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=page_size,
                    fields="files(id, name, size, md5Checksum, createdTime)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    corpora="drive",
                    driveId=self.shared_drive.drive_id,
                )
                .execute()
            )

            return results.get("files", [])

        except HttpError as e:
            logger.error(f"List files failed: {e}")
            raise

    def move_file(self, file_id: str, new_parent_folder_id: str) -> bool:
        """
        Move file to different folder

        Args:
            file_id: File ID to move
            new_parent_folder_id: Target folder ID

        Returns:
            True if successful
        """
        try:
            # Get current parents
            file = (
                self.service.files()
                .get(fileId=file_id, fields="parents", supportsAllDrives=True)
                .execute()
            )

            previous_parents = ",".join(file.get("parents", []))

            # Move file
            self.service.files().update(
                fileId=file_id,
                addParents=new_parent_folder_id,
                removeParents=previous_parents,
                supportsAllDrives=True,
            ).execute()

            logger.info(f"Moved file {file_id} to folder {new_parent_folder_id}")
            return True

        except HttpError as e:
            logger.error(f"Move file failed: {e}")
            raise

    def download_file(self, file_id: str, destination_path: str) -> bool:
        """
        Download file from drive to local storage

        Args:
            file_id: File ID to download
            destination_path: Local path to save file

        Returns:
            True if successful
        """
        try:
            request = self.service.files().get_media(
                fileId=file_id, supportsAllDrives=True
            )

            fh = io.FileIO(destination_path, "wb")
            downloader = MediaIoBaseDownload(fh, request, chunksize=self.CHUNK_SIZE)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Download progress: {progress}%")

            fh.close()
            logger.info(f"Downloaded file {file_id} to {destination_path}")
            return True

        except HttpError as e:
            logger.error(f"Download failed: {e}")
            raise

    def verify_file_integrity(self, file_id: str, expected_md5: str) -> bool:
        """
        Verify file integrity using MD5 checksum

        Args:
            file_id: File ID to verify
            expected_md5: Expected MD5 hash

        Returns:
            True if MD5 matches
        """
        file_info = self.get_file_info(file_id)

        if not file_info:
            return False

        actual_md5 = file_info.get("md5Checksum")

        if not actual_md5:
            logger.warning(f"No MD5 checksum available for {file_id}")
            return False

        matches = actual_md5 == expected_md5

        if not matches:
            logger.error(
                f"MD5 mismatch for {file_id}: expected={expected_md5}, actual={actual_md5}"
            )

        return matches
