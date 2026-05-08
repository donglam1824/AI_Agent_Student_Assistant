/**
 * components/docs/DriveBrowser.tsx
 * Google Drive file browser with folder navigation and file selection.
 * Allows users to browse their Drive, select files, and import into ORCA RAG.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getDriveFolders,
  getDriveFiles,
  importDriveFiles,
  syncDriveFile,
  type DriveFolder,
  type DriveFile,
  type DriveImportResult,
} from "@/lib/api";

// ── Icon helpers ──────────────────────────────────────────────────────────

function getMimeIcon(typeLabel: string): string {
  const icons: Record<string, string> = {
    "Google Docs": "📄",
    "Google Sheets": "📊",
    "Google Slides": "📊",
    "PDF": "📕",
    "DOCX": "📘",
    "TXT": "📃",
  };
  return icons[typeLabel] || "📄";
}

function formatSize(bytes: number): string {
  if (bytes === 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(isoDate: string): string {
  if (!isoDate) return "—";
  return new Date(isoDate).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

// ── Types ─────────────────────────────────────────────────────────────────

interface BreadcrumbItem {
  id: string | null;
  name: string;
}

// ── Main Component ────────────────────────────────────────────────────────

export function DriveBrowser() {
  const [folders, setFolders] = useState<DriveFolder[]>([]);
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([
    { id: null, name: "My Drive" },
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
        getDriveFolders(folderId),
        getDriveFiles(folderId),
      ]);
      setFolders(foldersData);
      setFiles(filesData);
      setSelectedIds(new Set());
      setImportResults([]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(`Không thể tải nội dung Drive: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadContents(currentFolderId);
  }, []);

  // Navigate into a folder
  const navigateToFolder = (folder: DriveFolder) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
    loadContents(folder.id);
  };

  // Navigate via breadcrumb
  const navigateToBreadcrumb = (index: number) => {
    const newBreadcrumbs = breadcrumbs.slice(0, index + 1);
    setBreadcrumbs(newBreadcrumbs);
    const targetId = newBreadcrumbs[newBreadcrumbs.length - 1].id ?? undefined;
    loadContents(targetId);
  };

  // Toggle file selection
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

  // Import selected files
  const handleImport = async () => {
    if (selectedIds.size === 0) return;
    setImporting(true);
    setImportResults([]);
    setError(null);
    try {
      const results = await importDriveFiles(Array.from(selectedIds));
      setImportResults(results);
      setSelectedIds(new Set());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(`Import thất bại: ${msg}`);
    } finally {
      setImporting(false);
    }
  };

  // Sync a single file
  const handleSync = async (fileId: string, fileName: string) => {
    setSyncing(fileId);
    try {
      const result = await syncDriveFile(fileId);
      alert(`${result.message}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      alert(`Sync thất bại: ${msg}`);
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="drive-browser">
      {/* Header */}
      <div className="drive-header">
        <div className="drive-title">
          <svg width="20" height="20" viewBox="0 0 87.3 78" className="drive-icon">
            <path d="M6.6 66.85L1.2 76.6a5 5 0 0 0 4.33 7.4h76.7a5 5 0 0 0 4.33-7.4l-5.4-9.75z" fill="#0066DA"/>
            <path d="M43.65 0L6.6 66.85h37.05z" fill="#00AC47"/>
            <path d="M43.65 0l37.05 66.85H43.65z" fill="#EA4335"/>
            <path d="M6.6 66.85l37.05-33.43L80.7 66.85z" fill="#00832D"/>
          </svg>
          <span>Google Drive</span>
        </div>
        <button
          className="drive-refresh-btn"
          onClick={() => loadContents(currentFolderId)}
          disabled={loading}
          title="Tải lại"
        >
          {loading ? "⏳" : "🔄"}
        </button>
      </div>

      {/* Breadcrumbs */}
      <div className="drive-breadcrumbs">
        {breadcrumbs.map((crumb, i) => (
          <span key={i} className="breadcrumb-item">
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

      {/* Error */}
      {error && (
        <div className="drive-error">
          <span>⚠️ {error}</span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="drive-loading">
          <div className="drive-spinner" />
          <span>Đang tải...</span>
        </div>
      )}

      {/* Import Results */}
      {importResults.length > 0 && (
        <div className="import-results">
          <h4>Kết quả import:</h4>
          {importResults.map((r) => (
            <div
              key={r.file_id}
              className={`import-result-item ${r.status}`}
            >
              {r.status === "success" ? "✅" : "❌"}{" "}
              <strong>{r.file_name}</strong> —{" "}
              {r.status === "success"
                ? `${r.num_chunks} chunks đã lưu`
                : `Lỗi: ${r.error}`}
            </div>
          ))}
        </div>
      )}

      {/* File browser */}
      {!loading && (
        <div className="drive-content">
          {/* Folders */}
          {folders.length > 0 && (
            <div className="drive-section">
              <p className="drive-section-label">Thư mục</p>
              <div className="drive-folders-grid">
                {folders.map((folder) => (
                  <button
                    key={folder.id}
                    className="drive-folder-item"
                    onClick={() => navigateToFolder(folder)}
                  >
                    <span className="folder-icon">📁</span>
                    <span className="folder-name">{folder.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Files */}
          {files.length > 0 ? (
            <div className="drive-section">
              <div className="drive-files-header">
                <p className="drive-section-label">
                  Tài liệu ({files.length} file hỗ trợ)
                </p>
                <button className="select-all-btn" onClick={toggleSelectAll}>
                  {selectedIds.size === files.length && files.length > 0
                    ? "Bỏ chọn tất cả"
                    : "Chọn tất cả"}
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
                      id={`drive-file-${file.id}`}
                    />
                    <span className="file-type-icon">
                      {getMimeIcon(file.type_label)}
                    </span>
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
                        handleSync(file.id, file.name);
                      }}
                      disabled={syncing === file.id}
                      title="Re-sync file này"
                    >
                      {syncing === file.id ? "⏳" : "🔄"}
                    </button>
                  </div>
                ))}
              </div>

              {/* Import button */}
              {selectedIds.size > 0 && (
                <div className="import-bar">
                  <span className="import-count">
                    {selectedIds.size} file đã chọn
                  </span>
                  <button
                    className="import-btn"
                    onClick={handleImport}
                    disabled={importing}
                    id="drive-import-btn"
                  >
                    {importing ? (
                      <>
                        <span className="import-spinner" />
                        Đang import...
                      </>
                    ) : (
                      <>☁️ Import vào ORCA</>
                    )}
                  </button>
                </div>
              )}
            </div>
          ) : (
            !loading && (
              <div className="drive-empty">
                <p>Không tìm thấy tài liệu được hỗ trợ trong thư mục này.</p>
                <p className="drive-empty-hint">
                  Hỗ trợ: Google Docs, Sheets, Slides, PDF, DOCX, TXT
                </p>
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
