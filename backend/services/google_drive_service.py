"""
Service kết nối Google Drive API để duyệt và tải file (PDF, DOCX, Google Docs...).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

from core.logger import logger

GOOGLE_EXPORT_MAP = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

# Map binary files sang extension tương ứng
BINARY_DOWNLOAD_MAP = {
    "application/pdf":                                                          ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
}

SUPPORTED_MIMES = set(GOOGLE_EXPORT_MAP.keys()) | set(BINARY_DOWNLOAD_MAP.keys())
FOLDER_MIME = "application/vnd.google-apps.folder"


@dataclass
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_time: str
    size: int = 0
    parents: List[str] = field(default_factory=list)

    @property
    def is_supported(self) -> bool:
        return self.mime_type in SUPPORTED_MIMES

    @property
    def type_label(self) -> str:
        labels = {
            "application/vnd.google-apps.document":     "Google Docs",
            "application/vnd.google-apps.spreadsheet":  "Google Sheets",
            "application/vnd.google-apps.presentation": "Google Slides",
            "application/pdf":                          "PDF",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPTX",
            "text/plain": "TXT",
        }
        return labels.get(self.mime_type, "Không hỗ trợ")


@dataclass
class DriveFolder:
    id: str
    name: str
    parents: List[str] = field(default_factory=list)


class GoogleDriveService:
    """Wrapper cho Google Drive API v3"""

    def __init__(self, access_token: str, refresh_token: str = ""):
        """Khởi tạo với Google OAuth credentials"""
        from config.settings import settings
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token or None,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        self._svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        logger.info("[GoogleDriveService] Khởi tạo thành công")

    def list_folders(self, parent_id: Optional[str] = None) -> List[DriveFolder]:
        """Liệt kê thư mục trong Drive"""
        if parent_id:
            q = f"mimeType='{FOLDER_MIME}' and '{parent_id}' in parents and trashed=false"
        else:
            q = f"mimeType='{FOLDER_MIME}' and trashed=false"

        try:
            result = self._svc.files().list(
                q=q,
                fields="files(id, name, parents)",
                orderBy="name",
                pageSize=100,
            ).execute()
        except Exception as e:
            logger.error(f"[GoogleDriveService] list_folders error: {e}")
            raise

        folders = []
        for f in result.get("files", []):
            folders.append(DriveFolder(
                id=f["id"],
                name=f["name"],
                parents=f.get("parents", []),
            ))
        logger.info(f"[GoogleDriveService] Tìm thấy {len(folders)} thư mục")
        return folders

    def list_files(
        self,
        folder_id: Optional[str] = None,
        max_results: int = 50,
    ) -> List[DriveFile]:
        """Liệt kê các file được hỗ trợ trong thư mục"""
        mime_conditions = " or ".join(
            f"mimeType='{m}'" for m in SUPPORTED_MIMES
        )

        if folder_id:
            q = f"({mime_conditions}) and '{folder_id}' in parents and trashed=false"
        else:
            q = f"({mime_conditions}) and trashed=false"

        try:
            result = self._svc.files().list(
                q=q,
                fields="files(id, name, mimeType, modifiedTime, size, parents)",
                orderBy="modifiedTime desc",
                pageSize=min(max_results, 100),
            ).execute()
        except Exception as e:
            logger.error(f"[GoogleDriveService] list_files error: {e}")
            raise

        files = []
        for f in result.get("files", []):
            files.append(DriveFile(
                id=f["id"],
                name=f["name"],
                mime_type=f["mimeType"],
                modified_time=f.get("modifiedTime", ""),
                size=int(f.get("size", 0)),
                parents=f.get("parents", []),
            ))

        logger.info(f"[GoogleDriveService] Tìm thấy {len(files)} file được hỗ trợ")
        return files

    def get_file_metadata(self, file_id: str) -> dict:
        try:
            return self._svc.files().get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, size",
            ).execute()
        except Exception as e:
            logger.error(f"[GoogleDriveService] get_file_metadata error: {e}")
            raise

    def get_file_content(self, file: DriveFile) -> Tuple[str, bytes]:
        """Tải nội dung file và trả về tuple (extension, bytes)"""
        mime = file.mime_type

        if mime in GOOGLE_EXPORT_MAP:
            export_mime = GOOGLE_EXPORT_MAP[mime]
            ext = ".csv" if "csv" in export_mime else ".txt"
            content = self._export_google_file(file.id, export_mime)
            return ext, content

        elif mime in BINARY_DOWNLOAD_MAP:
            ext = BINARY_DOWNLOAD_MAP[mime]
            content = self._download_binary(file.id)
            return ext, content

        else:
            raise ValueError(f"MIME type không được hỗ trợ: {mime}")

    def _export_google_file(self, file_id: str, export_mime: str) -> bytes:
        """Xuất Google Docs/Sheets sang dạng bytes"""
        try:
            logger.info(f"[GoogleDriveService] Export file {file_id} → {export_mime}")
            response = self._svc.files().export(
                fileId=file_id,
                mimeType=export_mime,
            ).execute()
            if isinstance(response, bytes):
                return response
            return str(response).encode("utf-8")
        except Exception as e:
            logger.error(f"[GoogleDriveService] export error file {file_id}: {e}")
            raise

    def _download_binary(self, file_id: str) -> bytes:
        """Tải file nhị phân trực tiếp"""
        try:
            logger.info(f"[GoogleDriveService] Download file {file_id}")
            request = self._svc.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"[GoogleDriveService] download error file {file_id}: {e}")
            raise


def build_drive_service_for_user(user) -> GoogleDriveService:
    """Khởi tạo GoogleDriveService từ User ORM bằng cách giải mã token"""
    from core.crypto import decrypt_token

    if not user.google_access_token:
        raise ValueError(f"User {user.email} chưa có Google access token.")

    access_token = decrypt_token(user.google_access_token)
    refresh_token = decrypt_token(user.google_refresh_token) if user.google_refresh_token else ""
    if not access_token:
        raise ValueError(f"Khong the giai ma Google access token cho user {user.email}.")

    return GoogleDriveService(
        access_token=access_token,
        refresh_token=refresh_token,
    )
