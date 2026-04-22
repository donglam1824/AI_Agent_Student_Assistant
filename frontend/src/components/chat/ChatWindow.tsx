/**
 * components/chat/ChatWindow.tsx
 * Main chat container – messages area with auto-scroll and empty state.
 */

"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "./ChatMessage";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types";
import {
  Calendar,
  StickyNote,
  Mail,
  BookOpen,
} from "lucide-react";

const SUGGESTIONS = [
  {
    icon: Calendar,
    text: "Tuần này tôi có lịch gì?",
    color: "text-blue-400",
  },
  {
    icon: StickyNote,
    text: "Ghi lại: Nộp bài tập môn CSDL trước thứ 6",
    color: "text-amber-400",
  },
  {
    icon: Mail,
    text: "Kiểm tra email mới từ giảng viên",
    color: "text-purple-400",
  },
  {
    icon: BookOpen,
    text: "Tìm công thức tích phân trong tài liệu Giải tích",
    color: "text-orange-400",
  },
];

interface ChatWindowProps {
  messages: ChatMessageType[];
  onSuggestionClick?: (text: string) => void;
}

export function ChatWindow({ messages, onSuggestionClick }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 animate-fade-in">
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">🐋</div>
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Xin chào! Mình là ORCA
          </h2>
          <p className="text-sm text-text-secondary max-w-md">
            Trợ lý AI học tập cá nhân của bạn. Hãy hỏi mình bất cứ điều gì về
            lịch học, ghi chú, email, hay tài liệu môn học.
          </p>
        </div>

        {/* Suggestion cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
          {SUGGESTIONS.map(({ icon: Icon, text, color }) => (
            <button
              key={text}
              onClick={() => onSuggestionClick?.(text)}
              className={cn(
                "flex items-start gap-3 p-3.5 rounded-xl text-left",
                "bg-bg-secondary border border-border",
                "hover:border-accent/40 hover:bg-bg-elevated",
                "transition-all duration-150 group"
              )}
            >
              <Icon
                size={18}
                className={cn("flex-shrink-0 mt-0.5", color)}
              />
              <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                {text}
              </span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Messages list
  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg) => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
