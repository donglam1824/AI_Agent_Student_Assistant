"""
services/onedrive_service.py
----------------------------
Read-only OneDrive integration through Microsoft Graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import requests

from core.logger import logger

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

BINARY_DOWNLOAD_MAP = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
}

SUPPORTED_MIMES = set(BINARY_DOWNLOAD_MAP.keys())


@dataclass
class OneDriveFile:
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
            "application/pdf": "PDF",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPTX",
            "text/plain": "TXT",
        }
        return labels.get(self.mime_type, "Khong ho tro")


@dataclass
class OneDriveFolder:
    id: str
    name: str
    parents: List[str] = field(default_factory=list)


class OneDriveService:
    """Minimal Microsoft Graph client for browsing and downloading OneDrive files."""

    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("Microsoft access token is required.")
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        logger.info("[OneDriveService] Initialized")

    def _get_json(self, path_or_url: str, params: Optional[dict] = None) -> dict:
        url = path_or_url if path_or_url.startswith("https://") else f"{GRAPH_ROOT}{path_or_url}"
        response = requests.get(url, headers=self._headers, params=params, timeout=30)
        if response.status_code >= 400:
            logger.error(f"[OneDriveService] GET {url} failed: {response.status_code} {response.text}")
        response.raise_for_status()
        return response.json()

    def _download(self, path: str) -> bytes:
        response = requests.get(f"{GRAPH_ROOT}{path}", headers=self._headers, timeout=60, allow_redirects=True)
        if response.status_code >= 400:
            logger.error(f"[OneDriveService] download {path} failed: {response.status_code} {response.text}")
        response.raise_for_status()
        return response.content

    def _list_children(self, parent_id: Optional[str], max_results: int = 100) -> list[dict]:
        if parent_id:
            path = f"/me/drive/items/{parent_id}/children"
        else:
            path = "/me/drive/root/children"

        params = {
            "$select": "id,name,folder,file,lastModifiedDateTime,size,parentReference",
            "$orderby": "lastModifiedDateTime desc",
            "$top": min(max_results, 100),
        }
        items: list[dict] = []
        data = self._get_json(path, params=params)
        items.extend(data.get("value", []))

        while data.get("@odata.nextLink") and len(items) < max_results:
            data = self._get_json(data["@odata.nextLink"])
            items.extend(data.get("value", []))

        return items[:max_results]

    def list_folders(self, parent_id: Optional[str] = None) -> List[OneDriveFolder]:
        folders = []
        for item in self._list_children(parent_id=parent_id):
            if "folder" not in item:
                continue
            parent = item.get("parentReference", {}).get("id")
            folders.append(OneDriveFolder(
                id=item["id"],
                name=item["name"],
                parents=[parent] if parent else [],
            ))
        logger.info(f"[OneDriveService] Found {len(folders)} folders")
        return folders

    def list_files(self, folder_id: Optional[str] = None, max_results: int = 50) -> List[OneDriveFile]:
        files = []
        for item in self._list_children(parent_id=folder_id, max_results=max_results):
            file_info = item.get("file")
            if not file_info:
                continue
            mime_type = file_info.get("mimeType", "")
            if mime_type not in SUPPORTED_MIMES:
                continue
            parent = item.get("parentReference", {}).get("id")
            files.append(OneDriveFile(
                id=item["id"],
                name=item["name"],
                mime_type=mime_type,
                modified_time=item.get("lastModifiedDateTime", ""),
                size=int(item.get("size", 0)),
                parents=[parent] if parent else [],
            ))
        logger.info(f"[OneDriveService] Found {len(files)} supported files")
        return files

    def get_file_metadata(self, file_id: str) -> dict:
        item = self._get_json(
            f"/me/drive/items/{file_id}",
            params={"$select": "id,name,file,lastModifiedDateTime,size,parentReference"},
        )
        file_info = item.get("file") or {}
        return {
            "id": item.get("id", file_id),
            "name": item.get("name", file_id),
            "mimeType": file_info.get("mimeType", ""),
            "modifiedTime": item.get("lastModifiedDateTime", ""),
            "size": item.get("size", 0),
        }

    def get_file_content(self, file: OneDriveFile) -> Tuple[str, bytes]:
        if file.mime_type not in BINARY_DOWNLOAD_MAP:
            raise ValueError(f"MIME type khong duoc ho tro: {file.mime_type}")
        ext = BINARY_DOWNLOAD_MAP[file.mime_type]
        return ext, self._download(f"/me/drive/items/{file.id}/content")
