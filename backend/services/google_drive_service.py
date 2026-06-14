"""
services/google_drive_service.py
---------------------------------
GoogleDriveService: kết nối Google Drive API để:
  - Liệt kê thư mục và file của người dùng
  - Export Google Docs/Sheets/Slides sang text
  - Download file thông thường (PDF, DOCX, PPTX, TXT)
  - Lấy metadata file (name, modifiedTime, size)

Hỗ trợ MIME types:
  - Google Docs      → export text/plain
  - Google Sheets    → export text/csv
  - Google Slides    → export text/plain
  - PDF, DOCX, PPTX, TXT → download trực tiếp
  - Khác             → bỏ qua
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

from core.logger import logger

# ── MIME type mappings ──────────────────────────────────────────────────────

# Google Workspace native types → export MIME
GOOGLE_EXPORT_MAP = {
    "application/vnd.google-apps.document":     "text/plain",
    "application/vnd.google-apps.spreadsheet":  "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

# Binary file types → download trực tiếp + extension để parse
BINARY_DOWNLOAD_MAP = {
    "application/pdf":                                                          ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
}

# Tất cả MIME được chấp nhận
SUPPORTED_MIMES = set(GOOGLE_EXPORT_MAP.keys()) | set(BINARY_DOWNLOAD_MAP.keys())

# Google Drive folder type
FOLDER_MIME = "application/vnd.google-apps.folder"


# ── Data models ─────────────────────────────────────────────────────────────

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


# ── Service ─────────────────────────────────────────────────────────────────

class GoogleDriveService:
    """Quản lý tương tác với Google Drive API v3."""

    def __init__(self, access_token: str, refresh_token: str = ""):
        """
        Khởi tạo service từ access_token (lấy từ DB người dùng).

        Args:
            access_token: Google OAuth2 access token của user.
            refresh_token: Refresh token để gia hạn tự động (tùy chọn).
        """
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

    # ── List operations ──────────────────────────────────────────────────

    def list_folders(self, parent_id: Optional[str] = None) -> List[DriveFolder]:
        """
        List thư mục trong Drive (hoặc trong một thư mục cha).

        Args:
            parent_id: ID thư mục cha. None = root Drive.
        Returns:
            Danh sách DriveFolder.
        """
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
        """
        List file được hỗ trợ trong Drive (hoặc trong thư mục cụ thể).
        Chỉ trả về MIME types được hỗ trợ.

        Args:
            folder_id: ID thư mục. None = toàn bộ Drive.
            max_results: Số file tối đa trả về.
        Returns:
            Danh sách DriveFile đã lọc.
        """
        # Xây dựng MIME filter
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
        """Lấy metadata của một file."""
        try:
            return self._svc.files().get(
                fileId=file_id,
                fields="id, name, mimeType, modifiedTime, size",
            ).execute()
        except Exception as e:
            logger.error(f"[GoogleDriveService] get_file_metadata error: {e}")
            raise

    # ── Content extraction ───────────────────────────────────────────────

    def get_file_content(self, file: DriveFile) -> Tuple[str, bytes]:
        """
        Lấy nội dung file từ Drive.

        Returns:
            Tuple (extension, content_bytes)
            - extension: ".txt", ".pdf", ".docx", ".pptx", ".csv"
            - content_bytes: nội dung nhị phân của file
        """
        mime = file.mime_type

        if mime in GOOGLE_EXPORT_MAP:
            # Google Workspace → export
            export_mime = GOOGLE_EXPORT_MAP[mime]
            ext = ".csv" if "csv" in export_mime else ".txt"
            content = self._export_google_file(file.id, export_mime)
            return ext, content

        elif mime in BINARY_DOWNLOAD_MAP:
            # File thông thường → download
            ext = BINARY_DOWNLOAD_MAP[mime]
            content = self._download_binary(file.id)
            return ext, content

        else:
            raise ValueError(f"MIME type không được hỗ trợ: {mime}")

    def _export_google_file(self, file_id: str, export_mime: str) -> bytes:
        """Export Google Workspace file sang text/plain hoặc text/csv."""
        try:
            logger.info(f"[GoogleDriveService] Export file {file_id} → {export_mime}")
            response = self._svc.files().export(
                fileId=file_id,
                mimeType=export_mime,
            ).execute()
            # export() returns bytes
            if isinstance(response, bytes):
                return response
            return str(response).encode("utf-8")
        except Exception as e:
            logger.error(f"[GoogleDriveService] export error file {file_id}: {e}")
            raise

    def _download_binary(self, file_id: str) -> bytes:
        """Download binary file từ Drive."""
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


# ── Helper: build service từ user credentials trong DB ──────────────────────

def build_drive_service_for_user(user) -> GoogleDriveService:
    """
    Tạo GoogleDriveService từ User ORM object (đã có token trong DB).

    Args:
        user: User SQLAlchemy model với google_access_token.
    Returns:
        GoogleDriveService instance.
    Raises:
        ValueError: Nếu user không có Google token.
    """
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
