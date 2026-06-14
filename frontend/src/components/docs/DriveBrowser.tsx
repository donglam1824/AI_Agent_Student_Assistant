/**
 * Cloud file browser for Google Drive and OneDrive document imports.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getDriveFolders,
  getDriveFiles,
  importDriveFiles,
  syncDriveFile,
  getOneDriveFolders,
  getOneDriveFiles,
  importOneDriveFiles,
  syncOneDriveFile,
  type DriveFolder,
  type DriveFile,
  type DriveImportResult,
} from "@/lib/api";

type DriveProvider = "google" | "onedrive";

interface BreadcrumbItem {
  id: string | null;
  name: string;
}

interface DriveBrowserProps {
  provider?: DriveProvider;
}

const PROVIDER_CONFIG = {
  google: {
    title: "Google Drive",
    rootName: "My Drive",
    loadError: "Khong the tai noi dung Google Drive",
    importError: "Import tu Google Drive that bai",
    syncError: "Sync Google Drive that bai",
    hint: "Ho tro: Google Docs, Sheets, Slides, PDF, DOCX, PPTX, TXT",
  },
  onedrive: {
    title: "OneDrive",
    rootName: "OneDrive",
    loadError: "Khong the tai noi dung OneDrive",
    importError: "Import tu OneDrive that bai",
    syncError: "Sync OneDrive that bai",
    hint: "Ho tro: PDF, DOCX, PPTX, TXT",
  },
} as const;

function getMimeIcon(typeLabel: string): string {
  const icons: Record<string, string> = {
    "Google Docs": "DOC",
    "Google Sheets": "XLS",
    "Google Slides": "PPT",
    PDF: "PDF",
    DOCX: "DOC",
    PPTX: "PPT",
    TXT: "TXT",
  };
  return icons[typeLabel] || "DOC";
}

function formatSize(bytes: number): string {
  if (bytes === 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoDate: string): string {
  if (!isoDate) return "-";
  return new Date(isoDate).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function ProviderIcon({ provider }: { provider: DriveProvider }) {
  if (provider === "onedrive") {
    return (
      <svg width="22" height="18" viewBox="0 0 22 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M8.6 4.9A5.2 5.2 0 0 1 18 8a4.9 4.9 0 0 1-.1 9.8H5.4A4.6 4.6 0 0 1 4 8.8a5.7 5.7 0 0 1 4.6-3.9Z" fill="#0078D4" />
        <path d="M8.6 4.9A5.7 5.7 0 0 1 14 1a5.8 5.8 0 0 1 5.6 4.4A4.9 4.9 0 0 0 18 8H9.4L4 8.8a5.7 5.7 0 0 1 4.6-3.9Z" fill="#1490DF" />
        <path d="M9.4 8H18a4.9 4.9 0 0 1-.1 9.8H9.4V8Z" fill="#0364B8" />
      </svg>
    );
  }

  return (
    <svg width="20" height="18" viewBox="0 0 24 20" className="drive-icon" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M8.3 1.4h7.4l7.4 12.8-3.7 6.4L8.3 1.4Z" fill="#EA4335" />
      <path d="M.9 14.2 8.3 1.4l3.7 6.4-7.4 12.8L.9 14.2Z" fill="#00AC47" />
      <path d="M4.6 20.6h14.8l3.7-6.4H8.3L4.6 20.6Z" fill="#2684FC" />
      <path d="m12 7.8 3.7 6.4H8.3L12 7.8Z" fill="#FFBA00" />
    </svg>
  );
}

export function DriveBrowser({ provider = "google" }: DriveBrowserProps) {
  const config = PROVIDER_CONFIG[provider];
  const [folders, setFolders] = useState<DriveFolder[]>([]);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { id: null, name: config.rootName },
  ]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [importResults, setImportResults] = useState<DriveImportResult[]>([]);

  const currentFolderId = breadcrumbs[breadcrumbs.length - 1].id ?? undefined;

  const loadContents = useCallback(async (folderId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const [foldersData, filesData] = await Promise.all([
        provider === "google" ? getDriveFolders(folderId) : getOneDriveFolders(folderId),
        provider === "google" ? getDriveFiles(folderId) : getOneDriveFiles(folderId),
      ]);
      setFolders(foldersData);
      setFiles(filesData);
      setSelectedIds(new Set());
      setImportResults([]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(`${config.loadError}: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, [config.loadError, provider]);

  useEffect(() => {
    void Promise.resolve().then(() => loadContents());
  }, [loadContents]);

  const navigateToFolder = (folder: DriveFolder) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
    loadContents(folder.id);
  };

  const navigateToBreadcrumb = (index: number) => {
    const newBreadcrumbs = breadcrumbs.slice(0, index + 1);
    setBreadcrumbs(newBreadcrumbs);
    const targetId = newBreadcrumbs[newBreadcrumbs.length - 1].id ?? undefined;
    loadContents(targetId);
  };

  const toggleSelect = (fileId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(fileId)) next.delete(fileId);
      else next.add(fileId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === files.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(files.map((f) => f.id)));
    }
  };

  const handleImport = async () => {
    if (selectedIds.size === 0) return;
    setImporting(true);
    setImportResults([]);
    setError(null);
    try {
      const ids = Array.from(selectedIds);
      const results = provider === "google" ? await importDriveFiles(ids) : await importOneDriveFiles(ids);
      setImportResults(results);
      setSelectedIds(new Set());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(`${config.importError}: ${msg}`);
    } finally {
      setImporting(false);
    }
  };

  const handleSync = async (fileId: string) => {
    setSyncing(fileId);
    try {
      const result = provider === "google" ? await syncDriveFile(fileId) : await syncOneDriveFile(fileId);
      alert(result.message);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      alert(`${config.syncError}: ${msg}`);
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="drive-browser">
      <div className="drive-header">
        <div className="drive-title">
          <ProviderIcon provider={provider} />
          <span>{config.title}</span>
        </div>
        <button
          className="drive-refresh-btn"
          onClick={() => loadContents(currentFolderId)}
          disabled={loading}
          title="Tai lai"
        >
          {loading ? "..." : "Reload"}
        </button>
      </div>

      <div className="drive-breadcrumbs">
        {breadcrumbs.map((crumb, i) => (
          <span key={`${crumb.id ?? "root"}-${i}`} className="breadcrumb-item">
            {i > 0 && <span className="breadcrumb-sep">/</span>}
            <button
              className={`breadcrumb-btn ${i === breadcrumbs.length - 1 ? "active" : ""}`}
              onClick={() => navigateToBreadcrumb(i)}
            >
              {crumb.name}
            </button>
          </span>
        ))}
      </div>

      {error && (
        <div className="drive-error">
          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="drive-loading">
          <div className="drive-spinner" />
          <span>Dang tai...</span>
        </div>
      )}

      {importResults.length > 0 && (
        <div className="import-results">
          <h4>Ket qua import:</h4>
          {importResults.map((r) => (
            <div key={r.file_id} className={`import-result-item ${r.status}`}>
              <strong>{r.file_name}</strong>{" "}
              {r.status === "success" ? `${r.num_chunks} chunks da luu` : `Loi: ${r.error}`}
            </div>
          ))}
        </div>
      )}

      {!loading && (
        <div className="drive-content">
          {folders.length > 0 && (
            <div className="drive-section">
              <p className="drive-section-label">Thu muc</p>
              <div className="drive-folders-grid">
                {folders.map((folder) => (
                  <button key={folder.id} className="drive-folder-item" onClick={() => navigateToFolder(folder)}>
                    <span className="folder-icon">▣</span>
                    <span className="folder-name">{folder.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {files.length > 0 ? (
            <div className="drive-section">
              <div className="drive-files-header">
                <p className="drive-section-label">Tai lieu ({files.length} file ho tro)</p>
                <button className="select-all-btn" onClick={toggleSelectAll}>
                  {selectedIds.size === files.length && files.length > 0 ? "Bo chon tat ca" : "Chon tat ca"}
                </button>
              </div>

              <div className="drive-files-list">
                {files.map((file) => (
                  <div
                    key={file.id}
                    className={`drive-file-item ${selectedIds.has(file.id) ? "selected" : ""}`}
                    onClick={() => toggleSelect(file.id)}
                  >
                    <input
                      type="checkbox"
                      className="drive-file-checkbox"
                      checked={selectedIds.has(file.id)}
                      onChange={() => toggleSelect(file.id)}
                      onClick={(e) => e.stopPropagation()}
                      id={`${provider}-file-${file.id}`}
                    />
                    <span className="file-type-icon">{getMimeIcon(file.type_label)}</span>
                    <div className="file-info">
                      <span className="file-name">{file.name}</span>
                      <span className="file-meta">
                        <span className="file-type-badge">{file.type_label}</span>
                        <span>{formatSize(file.size)}</span>
                        <span>{formatDate(file.modified_time)}</span>
                      </span>
                    </div>
                    <button
                      className="sync-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSync(file.id);
                      }}
                      disabled={syncing === file.id}
                      title="Re-sync file nay"
                    >
                      {syncing === file.id ? "..." : "Sync"}
                    </button>
                  </div>
                ))}
              </div>

              {selectedIds.size > 0 && (
                <div className="import-bar">
                  <span className="import-count">{selectedIds.size} file da chon</span>
                  <button className="import-btn" onClick={handleImport} disabled={importing} id={`${provider}-import-btn`}>
                    {importing ? (
                      <>
                        <span className="import-spinner" />
                        Dang import...
                      </>
                    ) : (
                      <>Import vao ORCA</>
                    )}
                  </button>
                </div>
              )}
            </div>
          ) : (
            !loading && (
              <div className="drive-empty">
                <p>Khong tim thay tai lieu duoc ho tro trong thu muc nay.</p>
                <p className="drive-empty-hint">{config.hint}</p>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
