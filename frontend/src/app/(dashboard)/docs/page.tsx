/**
 * Documents page – Upload and manage RAG documents.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { DropZone } from "@/components/docs/DropZone";
import { DocumentList } from "@/components/docs/DocumentList";
import {
  getDocuments,
  uploadDocument,
  deleteDocument as deleteDocApi,
} from "@/lib/api";
import type { Document } from "@/types";

export default function DocsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const loadDocuments = useCallback(() => {
    getDocuments()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Poll for processing documents
  useEffect(() => {
    const hasProcessing = documents.some((d) => d.status === "processing");
    if (!hasProcessing) return;

    const interval = setInterval(loadDocuments, 3000);
    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  const handleUpload = useCallback(
    async (file: File) => {
      setIsUploading(true);
      try {
        const doc = await uploadDocument(file);
        setDocuments((prev) => [doc, ...prev]);
      } catch (err) {
        console.error("Upload error:", err);
      } finally {
        setIsUploading(false);
      }
    },
    []
  );

  const handleDelete = useCallback(
    async (docId: string) => {
      try {
        await deleteDocApi(docId);
        setDocuments((prev) => prev.filter((d) => d.id !== docId));
      } catch {
        // Silently handle
      }
    },
    []
  );

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-text-primary">
            📚 Tài liệu của bạn
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Tải lên tài liệu môn học để ORCA giúp bạn tìm kiếm thông tin
          </p>
        </div>

        {/* Upload zone */}
        <div className="mb-6">
          <DropZone onUpload={handleUpload} disabled={isUploading} />
          {isUploading && (
            <p className="text-xs text-accent mt-2 text-center animate-pulse">
              Đang tải lên...
            </p>
          )}
        </div>

        {/* Document list */}
        <DocumentList documents={documents} onDelete={handleDelete} />
      </div>
    </div>
  );
}
