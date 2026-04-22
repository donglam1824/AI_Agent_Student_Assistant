/**
 * components/sidebar/ChatHistory.tsx
 * Right sidebar showing chat conversation history grouped by date.
 */

"use client";

import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { formatRelativeDate, cn } from "@/lib/utils";
import type { ChatSummary } from "@/types";

interface ChatHistoryProps {
  onNewChat: () => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
}

export function ChatHistory({
  onNewChat,
  onSelectChat,
  onDeleteChat,
}: ChatHistoryProps) {
  const { chatHistory, activeChatId } = useAppStore();

  // Group chats by relative date
  const grouped = chatHistory.reduce<Record<string, ChatSummary[]>>(
    (acc, chat) => {
      const dateLabel = formatRelativeDate(chat.updated_at);
      if (!acc[dateLabel]) acc[dateLabel] = [];
      acc[dateLabel].push(chat);
      return acc;
    },
    {}
  );

  return (
    <div className="w-64 border-l border-border bg-bg-secondary flex flex-col h-full">
      {/* New chat button */}
      <div className="p-3 border-b border-border">
        <button
          id="new-chat-btn"
          onClick={onNewChat}
          className={cn(
            "w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl",
            "bg-accent text-text-on-accent text-sm font-medium",
            "hover:bg-accent-hover transition-colors duration-150"
          )}
        >
          <Plus size={16} />
          Cuộc trò chuyện mới
        </button>
      </div>

      {/* Chat list */}
      <div className="flex-1 overflow-y-auto py-2 px-2">
        {Object.keys(grouped).length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare size={24} className="mx-auto text-text-secondary mb-2 opacity-40" />
            <p className="text-xs text-text-secondary">Chưa có cuộc trò chuyện nào</p>
          </div>
        ) : (
          Object.entries(grouped).map(([dateLabel, chats]) => (
            <div key={dateLabel} className="mb-3">
              <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider px-2 mb-1">
                {dateLabel}
              </p>
              {chats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  className={cn(
                    "w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-left group",
                    "transition-colors duration-150",
                    activeChatId === chat.id
                      ? "bg-accent/10 text-accent"
                      : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
                  )}
                >
                  <MessageSquare size={14} className="flex-shrink-0 opacity-60" />
                  <span className="text-xs truncate flex-1">{chat.title}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteChat(chat.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-error/10 hover:text-error transition-all"
                    aria-label="Xóa"
                  >
                    <Trash2 size={12} />
                  </button>
                </button>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
