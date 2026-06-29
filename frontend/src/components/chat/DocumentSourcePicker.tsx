/** Modal chọn phạm vi tài liệu (RAG scope) cho chat */

"use client";

import { useMemo, useState } from "react";
import { Check, FileText, Layers, X } from "lucide-react";
import { cn, formatFileSize } from "@/lib/utils";
import type { ChatSourceScope, Document, TopicCategorySummary } from "@/types";

interface DocumentSourcePickerProps {
  open: boolean;
  documents: Document[];
  topicSummary: TopicCategorySummary[];
  currentScope: ChatSourceScope;
  onClose: () => void;
  onApply: (scope: ChatSourceScope) => void;
}

type PickerTab = "documents" | "topics";

export function DocumentSourcePicker({
  open,
  documents,
  topicSummary,
  currentScope,
  onClose,
  onApply,
}: DocumentSourcePickerProps) {
  const [tab, setTab] = useState<PickerTab>(
    currentScope.mode === "topic" ? "topics" : "documents"
  );
  const [selectedIds, setSelectedIds] = useState<string[]>(
    currentScope.mode === "documents" ? currentScope.document_ids : []
  );
  const [selectedTopic, setSelectedTopic] = useState<ChatSourceScope | null>(
    currentScope.mode === "topic" ? currentScope : null
  );

  const readyDocuments = useMemo(
    () => documents.filter((doc) => doc.status === "ready"),
    [documents]
  );

  if (!open) return null;

  const toggleDocument = (docId: string) => {
    setSelectedTopic(null);
    setSelectedIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  const applySelection = () => {
    if (tab === "documents" && selectedIds.length > 0) {
      onApply({ mode: "documents", document_ids: selectedIds });
      return;
    }
    if (tab === "topics" && selectedTopic) {
      onApply(selectedTopic);
      return;
    }
    onApply({ mode: "all" });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="flex h-[560px] max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-border bg-bg-primary shadow-xl">
        <div className="flex flex-shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Sử dụng tài liệu</h3>
            <p className="text-xs text-text-secondary">
              Khi chọn nguồn, chat chỉ tìm trong nguồn đó.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
            aria-label="Đóng"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex flex-shrink-0 border-b border-border px-4 pt-3">
          <button
            onClick={() => setTab("documents")}
            className={cn(
              "px-3 py-2 text-xs font-semibold border-b-2 transition-colors",
              tab === "documents"
                ? "border-accent text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            Tài liệu
          </button>
          <button
            onClick={() => setTab("topics")}
            className={cn(
              "px-3 py-2 text-xs font-semibold border-b-2 transition-colors",
              tab === "topics"
                ? "border-accent text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            Topic
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          {tab === "documents" && (
            <div className="space-y-2">
              {readyDocuments.length === 0 ? (
                <p className="py-8 text-center text-sm text-text-secondary">
                  Chưa có tài liệu sẵn sàng để chọn.
                </p>
              ) : (
                readyDocuments.map((doc) => {
                  const selected = selectedIds.includes(doc.id);
                  return (
                    <button
                      key={doc.id}
                      onClick={() => toggleDocument(doc.id)}
                      className={cn(
                        "flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors",
                        selected
                          ? "border-accent bg-accent/10"
                          : "border-border bg-bg-secondary hover:border-border-hover"
                      )}
                    >
                      <FileText size={17} className="mt-0.5 flex-shrink-0 text-accent" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium text-text-primary">
                          {doc.filename}
                        </div>
                        <div className="mt-1 flex flex-wrap gap-2 text-xs text-text-secondary">
                          <span>{formatFileSize(doc.file_size)}</span>
                          {doc.category && <span>{doc.category}</span>}
                          {doc.topic && <span>{doc.topic}</span>}
                        </div>
                      </div>
                      {selected && <Check size={16} className="text-accent" />}
                    </button>
                  );
                })
              )}
            </div>
          )}

          {tab === "topics" && (
            <div className="space-y-3">
              {topicSummary.length === 0 ? (
                <p className="py-8 text-center text-sm text-text-secondary">
                  Chưa có topic nào từ tài liệu sẵn sàng.
                </p>
              ) : (
                topicSummary.map((group) => (
                  <div key={group.category} className="rounded-lg border border-border bg-bg-secondary p-3">
                    <button
                      onClick={() => {
                        setSelectedIds([]);
                        setSelectedTopic({ mode: "topic", category: group.category });
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left transition-colors",
                        selectedTopic?.mode === "topic" &&
                          selectedTopic.category === group.category &&
                          !selectedTopic.topic
                          ? "bg-accent/10 text-text-primary"
                          : "text-text-primary hover:bg-bg-elevated"
                      )}
                    >
                      <Layers size={16} className="text-accent" />
                      <span className="flex-1 text-sm font-semibold">{group.category}</span>
                      <span className="text-xs text-text-secondary">{group.count} tài liệu</span>
                    </button>

                    {group.topics.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {group.topics.map((topic) => {
                          const selected =
                            selectedTopic?.mode === "topic" &&
                            selectedTopic.category === group.category &&
                            selectedTopic.topic === topic;
                          return (
                            <button
                              key={`${group.category}-${topic}`}
                              onClick={() => {
                                setSelectedIds([]);
                                setSelectedTopic({
                                  mode: "topic",
                                  category: group.category,
                                  topic,
                                });
                              }}
                              className={cn(
                                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                                selected
                                  ? "border-accent bg-accent/10 text-text-primary"
                                  : "border-border text-text-secondary hover:text-text-primary"
                              )}
                            >
                              {topic}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <div className="flex flex-shrink-0 items-center justify-between border-t border-border px-4 py-3">
          <button
            onClick={() => onApply({ mode: "all" })}
            className="rounded-lg px-3 py-2 text-xs font-medium text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
          >
            Dùng toàn bộ tài liệu
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-lg px-3 py-2 text-xs font-medium text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
            >
              Hủy
            </button>
            <button
              onClick={applySelection}
              className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-text-on-accent hover:bg-accent-hover"
            >
              Áp dụng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
