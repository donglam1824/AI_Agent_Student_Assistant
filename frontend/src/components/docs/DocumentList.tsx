/**
 * components/docs/DocumentList.tsx
 * Table/list of uploaded documents with status and actions.
 */

"use client";

import { FileText, Trash2, CheckCircle, Loader2, AlertCircle } from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import type { Document } from "@/types";

interface DocumentListProps {
  documents: Document[];
  onDelete: (docId: string) => void;
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
    colorClass: "text-warning animate-spin",
  },
  error: {
    icon: AlertCircle,
    label: "Lỗi",
    colorClass: "text-error",
  },
};

export function DocumentList({ documents, onDelete }: DocumentListProps) {
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
    <div className="space-y-2">
      {documents.map((doc) => {
        const status = STATUS_CONFIG[doc.status] || STATUS_CONFIG.error;
        const StatusIcon = status.icon;

        return (
          <div
            key={doc.id}
            className={cn(
              "flex items-center gap-3 p-3 rounded-xl",
              "bg-bg-secondary border border-border",
              "hover:border-border-hover transition-colors duration-150 group"
            )}
          >
            {/* File icon */}
            <div className="w-10 h-10 rounded-lg bg-bg-elevated flex items-center justify-center flex-shrink-0">
              <FileText size={18} className="text-accent" />
            </div>

            {/* File info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {doc.filename}
              </p>
              <div className="flex items-center gap-3 mt-0.5">
                <span className="text-xs text-text-secondary">
                  {formatFileSize(doc.file_size)}
                </span>
                {doc.status === "ready" && (
                  <span className="text-xs text-text-secondary">
                    {doc.chunk_count} phân đoạn
                  </span>
                )}
                {doc.error_message && (
                  <span className="text-xs text-error truncate">
                    {doc.error_message}
                  </span>
                )}
              </div>
            </div>

            {/* Status */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <StatusIcon size={14} className={status.colorClass} />
              <span className={cn("text-xs", status.colorClass)}>
                {status.label}
              </span>
            </div>

            {/* Delete button */}
            <button
              onClick={() => onDelete(doc.id)}
              className={cn(
                "p-2 rounded-lg flex-shrink-0",
                "opacity-0 group-hover:opacity-100",
                "hover:bg-error/10 text-text-secondary hover:text-error",
                "transition-all duration-150"
              )}
              aria-label="Xóa tài liệu"
            >
              <Trash2 size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
