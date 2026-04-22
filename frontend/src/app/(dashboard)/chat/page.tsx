/**
 * Chat AI page – main conversation interface with SSE streaming.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatHistory } from "@/components/sidebar/ChatHistory";
import { useChat } from "@/hooks/useChat";
import { useAppStore } from "@/lib/store";
import { getChatHistory, getChatMessages, deleteChat as deleteChatApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PanelRightOpen, PanelRightClose } from "lucide-react";

export default function ChatPage() {
  const {
    activeChatId,
    setActiveChatId,
    chatHistory,
    setChatHistory,
    removeChatFromHistory,
    addChatToHistory,
  } = useAppStore();

  const {
    messages,
    isLoading,
    sendMessage,
    setMessages,
    clearMessages,
  } = useChat(activeChatId);

  const [showHistory, setShowHistory] = useState(true);

  // Load chat history on mount
  useEffect(() => {
    getChatHistory()
      .then(setChatHistory)
      .catch(() => {
        // Fallback: if API not ready, use empty history
        setChatHistory([]);
      });
  }, [setChatHistory]);

  // Load messages when active chat changes
  useEffect(() => {
    if (activeChatId) {
      getChatMessages(activeChatId)
        .then((msgs) => setMessages(msgs))
        .catch(() => setMessages([]));
    }
  }, [activeChatId, setMessages]);

  const handleNewChat = useCallback(() => {
    setActiveChatId(null);
    clearMessages();
  }, [setActiveChatId, clearMessages]);

  const handleSelectChat = useCallback(
    (chatId: string) => {
      setActiveChatId(chatId);
    },
    [setActiveChatId]
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
      await sendMessage(text);
      // Refresh history after sending
      getChatHistory()
        .then(setChatHistory)
        .catch(() => {});
    },
    [sendMessage, setChatHistory]
  );

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
        <ChatInput
          onSend={handleSend}
          disabled={isLoading}
          placeholder={isLoading ? "Đang xử lý..." : "Nhập tin nhắn..."}
        />
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
