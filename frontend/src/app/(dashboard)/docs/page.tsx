/**
 * Documents page – Upload and manage RAG documents.
 * Tabs: Manual Upload | Google Drive
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { DropZone } from "@/components/docs/DropZone";
import { DocumentList } from "@/components/docs/DocumentList";
import { DriveBrowser } from "@/components/docs/DriveBrowser";
import { TopicOverview } from "@/components/docs/TopicOverview";
import {
  getDocuments,
  uploadDocument,
  deleteDocument as deleteDocApi,
  getTopicSummary,
} from "@/lib/api";
import type { Document, TopicCategorySummary } from "@/types";

type Tab = "upload" | "drive" | "onedrive";

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("upload");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [topicSummary, setTopicSummary] = useState<TopicCategorySummary[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const loadDocuments = useCallback(() => {
    getDocuments()
      .then(setDocuments)
      .catch(() => setDocuments([]));

    getTopicSummary()
      .then(setTopicSummary)
      .catch(() => setTopicSummary([]));
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
        // Trigger topic statistics refresh
        getTopicSummary()
          .then(setTopicSummary)
          .catch(() => {});
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
        // Trigger topic statistics refresh
        getTopicSummary()
          .then(setTopicSummary)
          .catch(() => {});
      } catch {
        // Silently handle
      }
    },
    []
  );

  // Filter documents by selected category
  const filteredDocuments = documents.filter((doc) => {
    if (!selectedCategory) return true;
    return doc.category === selectedCategory;
  });

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="max-w-3xl mx-auto">

        {/* Page header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-text-primary">
              Tài liệu của bạn
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Upload hoặc import tài liệu môn học để ORCA giúp bạn tìm kiếm thông tin
            </p>
          </div>
        </div>

        {/* Topic overview stats dashboard */}
        <TopicOverview
          summary={topicSummary}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        {/* Tab navigation */}
        <div className="docs-tab-nav" role="tablist">
          <button
            id="tab-upload"
            role="tab"
            aria-selected={activeTab === "upload"}
            className={`docs-tab-btn ${activeTab === "upload" ? "active" : ""}`}
            onClick={() => setActiveTab("upload")}
          >
            📤 Upload file
          </button>
          <button
            id="tab-drive"
            role="tab"
            aria-selected={activeTab === "drive"}
            className={`docs-tab-btn ${activeTab === "drive" ? "active" : ""}`}
            onClick={() => setActiveTab("drive")}
          >
            ☁️ Google Drive
          </button>
          <button
            id="tab-onedrive"
            role="tab"
            aria-selected={activeTab === "onedrive"}
            className={`docs-tab-btn ${activeTab === "onedrive" ? "active" : ""}`}
            onClick={() => setActiveTab("onedrive")}
          >
            OneDrive
          </button>
        </div>

        {/* Tab content */}
        {activeTab === "upload" && (
          <div className="docs-tab-content" role="tabpanel" aria-labelledby="tab-upload">
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
            <DocumentList
              documents={filteredDocuments}
              onDelete={handleDelete}
              onUpdate={loadDocuments}
            />
          </div>
        )}

        {activeTab === "drive" && (
          <div className="docs-tab-content" role="tabpanel" aria-labelledby="tab-drive">
            <DriveBrowser provider="google" />
          </div>
        )}

        {activeTab === "onedrive" && (
          <div className="docs-tab-content" role="tabpanel" aria-labelledby="tab-onedrive">
            <DriveBrowser provider="onedrive" />
          </div>
        )}

      </div>
    </div>
  );
}
