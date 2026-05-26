/**
 * components/docs/DocumentList.tsx
 * Table/list of uploaded documents with topic badges, inline editing, and actions.
 */

"use client";

import { useState } from "react";
import {
  FileText,
  Trash2,
  CheckCircle,
  Loader2,
  AlertCircle,
  Edit2,
  Check,
  X,
  Tag
} from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import type { Document } from "@/types";
import { getCategoryColors } from "./TopicOverview";
import { updateDocumentTopic } from "@/lib/api";

interface DocumentListProps {
  documents: Document[];
  onDelete: (docId: string) => void;
  onUpdate?: () => void;
}

const STATUS_CONFIG = {
  ready: {
    icon: CheckCircle,
    label: "Sẵn sàng",
    colorClass: "text-success",
  },
  processing: {
    icon: Loader2,
    label: "Đang xử lý",
    colorClass: "text-warning",
  },
  error: {
    icon: AlertCircle,
    label: "Lỗi",
    colorClass: "text-error",
  },
};

export function DocumentList({ documents, onDelete, onUpdate }: DocumentListProps) {
  // Editing State
  const [editingDocId, setEditingDocId] = useState<string | null>(null);
  const [editTopic, setEditTopic] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editTags, setEditTags] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const startEdit = (doc: Document) => {
    setEditingDocId(doc.id);
    setEditTopic(doc.topic || "");
    setEditCategory(doc.category || "");
    setEditTags(doc.tags ? doc.tags.join(", ") : "");
    setSaveError(null);
  };

  const cancelEdit = () => {
    setEditingDocId(null);
    setSaveError(null);
  };

  const handleSave = async (docId: string) => {
    if (!editTopic.trim() || !editCategory.trim()) {
      setSaveError("Vui lòng điền đầy đủ Chủ đề và Danh mục.");
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    try {
      const tagsArray = editTags
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      await updateDocumentTopic(docId, {
        topic: editTopic.trim(),
        category: editCategory.trim(),
        tags: tagsArray,
      });

      setEditingDocId(null);
      if (onUpdate) {
        onUpdate();
      }
    } catch (err: any) {
      console.error("Lỗi cập nhật chủ đề:", err);
      setSaveError(err.response?.data?.detail || "Không thể cập nhật chủ đề.");
    } finally {
      setIsSaving(false);
    }
  };

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText size={32} className="mx-auto text-text-secondary mb-3 opacity-30" />
        <p className="text-sm text-text-secondary">Chưa có tài liệu nào</p>
        <p className="text-xs text-text-secondary mt-1">
          Tải lên tài liệu để ORCA giúp bạn tìm kiếm thông tin
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => {
        const isEditing = editingDocId === doc.id;
        const status = STATUS_CONFIG[doc.status] || STATUS_CONFIG.error;
        const StatusIcon = status.icon;
        
        // Dynamic colors based on category
        const catColors = doc.category
          ? getCategoryColors(doc.category)
          : { bg: "rgba(255,255,255,0.05)", text: "var(--text-secondary)", border: "var(--border)", primary: "var(--text-muted)" };

        return (
          <div
            key={doc.id}
            className={cn(
              "flex flex-col md:flex-row md:items-center gap-3 p-4 rounded-xl border transition-all duration-150 relative group",
              "bg-bg-secondary border-border",
              isEditing ? "border-accent/50 bg-bg-secondary/80 shadow-md ring-1 ring-accent/20" : "hover:border-border-hover"
            )}
          >
            {/* Left Section: File Icon + File Info or Editing Fields */}
            <div className="flex items-start gap-3 flex-1 min-w-0">
              {/* File icon */}
              <div className="w-10 h-10 rounded-lg bg-bg-elevated flex items-center justify-center flex-shrink-0 mt-0.5">
                <FileText size={18} className="text-accent" />
              </div>

              {/* Main Document Content */}
              {isEditing ? (
                <div className="flex-1 space-y-2.5 min-w-0">
                  <div className="text-xs font-semibold text-text-primary mb-1 truncate">
                    Chỉnh sửa phân loại: <span className="text-accent">{doc.filename}</span>
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-text-secondary block mb-1">
                        Chủ đề chính (Topic) *
                      </label>
                      <input
                        type="text"
                        value={editTopic}
                        onChange={(e) => setEditTopic(e.target.value)}
                        placeholder="Ví dụ: Đại số tuyến tính, Lập trình Python"
                        disabled={isSaving}
                        className="w-full text-xs bg-bg-elevated border border-border focus:border-accent rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] uppercase tracking-wider font-semibold text-text-secondary block mb-1">
                        Danh mục (Category) *
                      </label>
                      <input
                        type="text"
                        value={editCategory}
                        onChange={(e) => setEditCategory(e.target.value)}
                        placeholder="Ví dụ: Toán, Công nghệ thông tin"
                        disabled={isSaving}
                        className="w-full text-xs bg-bg-elevated border border-border focus:border-accent rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="text-[10px] uppercase tracking-wider font-semibold text-text-secondary block mb-1">
                      Tags từ khóa (cách nhau bởi dấu phẩy)
                    </label>
                    <input
                      type="text"
                      value={editTags}
                      onChange={(e) => setEditTags(e.target.value)}
                      placeholder="Ví dụ: ma trận, định thức, vector"
                      disabled={isSaving}
                      className="w-full text-xs bg-bg-elevated border border-border focus:border-accent rounded-lg px-2.5 py-1.5 text-text-primary focus:outline-none"
                    />
                  </div>

                  {saveError && (
                    <p className="text-[10px] text-error font-medium">{saveError}</p>
                  )}
                </div>
              ) : (
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-text-primary truncate">
                      {doc.filename}
                    </p>
                    
                    {/* Category & Topic Badge */}
                    {doc.status === "ready" && doc.category && (
                      <span
                        className="text-[10px] font-bold px-2 py-0.5 rounded border flex items-center gap-1 flex-shrink-0"
                        style={{
                          backgroundColor: catColors.bg,
                          color: catColors.text,
                          borderColor: catColors.border,
                        }}
                      >
                        <span className="w-1 h-1 rounded-full" style={{ backgroundColor: catColors.primary }} />
                        {doc.category}
                      </span>
                    )}

                    {doc.status === "ready" && doc.topic && (
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-bg-elevated border border-border text-text-primary truncate max-w-[150px] flex-shrink-0" title={doc.topic}>
                        {doc.topic}
                      </span>
                    )}
                  </div>

                  {/* Details / File stats */}
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-text-secondary">
                    <span>{formatFileSize(doc.file_size)}</span>
                    {doc.status === "ready" && (
                      <>
                        <span className="text-text-muted">•</span>
                        <span>{doc.chunk_count} phân đoạn</span>
                      </>
                    )}
                    {doc.source_type && doc.source_type !== "manual_upload" && (
                      <>
                        <span className="text-text-muted">•</span>
                        <span className="text-[10px] uppercase font-bold tracking-wider text-accent/80">
                          {doc.source_type === "google_drive" ? "Google Drive" : "OneDrive"}
                        </span>
                      </>
                    )}
                    {doc.error_message && (
                      <span className="text-error truncate max-w-xs">{doc.error_message}</span>
                    )}
                  </div>

                  {/* Document Tags */}
                  {doc.status === "ready" && doc.tags && doc.tags.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      <Tag size={10} className="text-text-muted flex-shrink-0" />
                      <div className="flex flex-wrap gap-1">
                        {doc.tags.map((tag) => (
                          <span
                            key={tag}
                            className="text-[10px] font-semibold text-text-secondary bg-bg-elevated/40 hover:bg-bg-elevated border border-border/65 px-1.5 py-0.2 rounded transition-colors"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right Section: Status Badge & Edit/Save/Cancel Actions */}
            <div className="flex items-center justify-between md:justify-end gap-3 mt-2 md:mt-0 pt-2 md:pt-0 border-t border-border/40 md:border-t-0 flex-shrink-0">
              {/* Status */}
              {!isEditing && (
                <div className="flex items-center gap-1.5 min-w-[90px]">
                  <StatusIcon size={13} className={cn(status.colorClass, doc.status === "processing" && "animate-spin")} />
                  <span className={cn("text-xs font-medium", status.colorClass)}>
                    {status.label}
                  </span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-1 ml-auto md:ml-0">
                {isEditing ? (
                  <>
                    <button
                      onClick={() => handleSave(doc.id)}
                      disabled={isSaving}
                      className={cn(
                        "p-2 rounded-lg text-success hover:bg-success/10 transition-colors",
                        isSaving && "opacity-50 cursor-not-allowed"
                      )}
                      title="Lưu thay đổi"
                    >
                      {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                    </button>
                    <button
                      onClick={cancelEdit}
                      disabled={isSaving}
                      className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors"
                      title="Hủy bỏ"
                    >
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    {doc.status === "ready" && (
                      <button
                        onClick={() => startEdit(doc)}
                        className="p-2 rounded-lg opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-bg-elevated text-text-secondary hover:text-text-primary transition-all duration-150"
                        title="Chỉnh sửa chủ đề"
                      >
                        <Edit2 size={13} />
                      </button>
                    )}
                    <button
                      onClick={() => onDelete(doc.id)}
                      className="p-2 rounded-lg opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-error/10 text-text-secondary hover:text-error transition-all duration-150"
                      title="Xóa tài liệu"
                    >
                      <Trash2 size={13} />
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
