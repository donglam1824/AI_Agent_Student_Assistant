/**
 * Chat AI page – main conversation interface with SSE streaming.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { DocumentSourcePicker } from "@/components/chat/DocumentSourcePicker";
import { ChatHistory } from "@/components/sidebar/ChatHistory";
import { useChat } from "@/hooks/useChat";
import { useAppStore } from "@/lib/store";
import {
  getChatHistory,
  getChatMessages,
  deleteChat as deleteChatApi,
  getDocuments,
  uploadDocument,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { PanelRightOpen, PanelRightClose, X } from "lucide-react";
import type { ChatSourceScope, Document, TopicCategorySummary } from "@/types";

function scopeSummary(scope: ChatSourceScope) {
  if (scope.mode === "documents") {
    return `Nguồn: ${scope.document_ids.length} tài liệu đã chọn`;
  }
  if (scope.mode === "topic") {
    return `Nguồn: ${scope.topic ? `${scope.category} / ${scope.topic}` : scope.category}`;
  }
  return "Nguồn: toàn bộ tài liệu";
}

function buildTopicSummary(documents: Document[]): TopicCategorySummary[] {
  const map = new Map<string, { category: string; count: number; topics: Set<string> }>();
  documents
    .filter((doc) => doc.status === "ready" && doc.category)
    .forEach((doc) => {
      const category = doc.category || "";
      const entry = map.get(category) || { category, count: 0, topics: new Set<string>() };
      entry.count += 1;
      if (doc.topic) entry.topics.add(doc.topic);
      map.set(category, entry);
    });

  return Array.from(map.values())
    .map((entry) => ({
      category: entry.category,
      count: entry.count,
      topics: Array.from(entry.topics),
    }))
    .sort((a, b) => b.count - a.count);
}

export default function ChatPage() {
  const {
    activeChatId,
    setActiveChatId,
    chatHistory,
    setChatHistory,
    removeChatFromHistory,
  } = useAppStore();

  const {
    messages,
    isLoading,
    sendMessage,
    setMessages,
    clearMessages,
  } = useChat(activeChatId);

  const [showHistory, setShowHistory] = useState(true);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeSourceScope, setActiveSourceScope] = useState<ChatSourceScope>({ mode: "all" });
  const [isSourcePickerOpen, setIsSourcePickerOpen] = useState(false);
  const [sourceNotice, setSourceNotice] = useState<string | null>(null);

  const topicSummary = buildTopicSummary(documents);

  const loadDocumentSources = useCallback(() => {
    getDocuments()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  // Load chat history on mount
  useEffect(() => {
    getChatHistory()
      .then(setChatHistory)
      .catch(() => {
        // Fallback: if API not ready, use empty history
        setChatHistory([]);
      });
  }, [setChatHistory]);

  useEffect(() => {
    loadDocumentSources();
  }, [loadDocumentSources]);

  // Load messages when active chat changes
  useEffect(() => {
    if (activeChatId) {
      getChatMessages(activeChatId)
        .then((msgs) => {
          setMessages(msgs);
          const chat = chatHistory.find((item) => item.id === activeChatId);
          setActiveSourceScope(chat?.source_scope || { mode: "all" });
        })
        .catch(() => setMessages([]));
    }
  }, [activeChatId, chatHistory, setMessages]);

  const handleNewChat = useCallback(() => {
    setActiveChatId(null);
    clearMessages();
    setActiveSourceScope({ mode: "all" });
    setSourceNotice(null);
  }, [setActiveChatId, clearMessages]);

  const handleSelectChat = useCallback(
    (chatId: string) => {
      setActiveChatId(chatId);
      const chat = chatHistory.find((item) => item.id === chatId);
      setActiveSourceScope(chat?.source_scope || { mode: "all" });
      setSourceNotice(null);
    },
    [chatHistory, setActiveChatId]
  );

  const handleDeleteChat = useCallback(
    async (chatId: string) => {
      try {
        await deleteChatApi(chatId);
        removeChatFromHistory(chatId);
        if (activeChatId === chatId) {
          handleNewChat();
        }
      } catch {
        // Silently handle - API might not be ready
        removeChatFromHistory(chatId);
      }
    },
    [activeChatId, removeChatFromHistory, handleNewChat]
  );

  const handleSend = useCallback(
    async (text: string) => {
      await sendMessage(text, activeSourceScope);
      // Refresh history after sending
      getChatHistory()
        .then(setChatHistory)
        .catch(() => {});
    },
    [activeSourceScope, sendMessage, setChatHistory]
  );

  const handleFileUpload = useCallback(
    async (file: File) => {
      setSourceNotice("Đang tải lên tài liệu...");
      try {
        const doc = await uploadDocument(file);
        setDocuments((prev) => {
          const rest = prev.filter((item) => item.id !== doc.id);
          return [doc, ...rest];
        });
        setActiveSourceScope({ mode: "documents", document_ids: [doc.id] });
        setSourceNotice(
          doc.status === "ready"
            ? "Đã chọn tài liệu vừa tải lên làm nguồn chat."
            : "Tài liệu đang xử lý. Nguồn sẽ dùng được khi trạng thái sẵn sàng."
        );
        loadDocumentSources();
      } catch {
        setSourceNotice("Không thể tải lên tài liệu.");
      }
    },
    [loadDocumentSources]
  );

  const handleApplySourceScope = useCallback((scope: ChatSourceScope) => {
    setActiveSourceScope(scope);
    setIsSourcePickerOpen(false);
    setSourceNotice(null);
  }, []);

  const handleClearSourceScope = useCallback(() => {
    setActiveSourceScope({ mode: "all" });
    setSourceNotice(null);
  }, []);

  const handleSuggestionClick = useCallback(
    (text: string) => {
      handleSend(text);
    },
    [handleSend]
  );

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatWindow
          messages={messages}
          onSuggestionClick={handleSuggestionClick}
        />
        <div className="border-t border-border bg-bg-primary px-3 py-2">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-bg-secondary px-3 py-2 text-xs">
            <span className="text-text-secondary">{scopeSummary(activeSourceScope)}</span>
            <div className="flex items-center gap-2">
              {sourceNotice && <span className="text-accent">{sourceNotice}</span>}
              {activeSourceScope.mode !== "all" && (
                <button
                  onClick={handleClearSourceScope}
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
                >
                  <X size={12} />
                  Bỏ chọn
                </button>
              )}
            </div>
          </div>
        </div>
        <ChatInput
          onSend={handleSend}
          onFileUpload={handleFileUpload}
          onOpenSourcePicker={() => {
            loadDocumentSources();
            setIsSourcePickerOpen(true);
          }}
          disabled={isLoading}
          placeholder={isLoading ? "Đang xử lý..." : "Nhập tin nhắn..."}
        />
        {isSourcePickerOpen && (
          <DocumentSourcePicker
            open={isSourcePickerOpen}
            documents={documents}
            topicSummary={topicSummary}
            currentScope={activeSourceScope}
            onClose={() => setIsSourcePickerOpen(false)}
            onApply={handleApplySourceScope}
          />
        )}
      </div>

      {/* Toggle history button */}
      <button
        onClick={() => setShowHistory(!showHistory)}
        className={cn(
          "absolute top-16 right-2 z-10 p-2 rounded-lg",
          "bg-bg-secondary border border-border",
          "text-text-secondary hover:text-text-primary",
          "transition-colors duration-150",
          showHistory && "right-[264px]"
        )}
        aria-label={showHistory ? "Ẩn lịch sử" : "Hiện lịch sử"}
      >
        {showHistory ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
      </button>

      {/* Chat history sidebar */}
      {showHistory && (
        <ChatHistory
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
        />
      )}
    </div>
  );
}
