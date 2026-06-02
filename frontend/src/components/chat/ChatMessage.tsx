/**
 * components/chat/ChatMessage.tsx
 * Individual chat message bubble (user or AI).
 */

"use client";

import ReactMarkdown from "react-markdown";
import { AgentBadge } from "./AgentBadge";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/types";

interface ChatMessageProps {
  message: ChatMessageType;
}

function formatSourceScope(message: ChatMessageType) {
  const scope = message.source_scope;
  if (!scope || scope.mode === "all") return null;
  if (scope.mode === "documents") {
    return `Nguồn: ${scope.document_ids.length} tài liệu`;
  }
  return `Nguồn: ${scope.topic ? `${scope.category} / ${scope.topic}` : scope.category}`;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const sourceLabel = formatSourceScope(message);

  return (
    <div
      className={cn(
        "flex w-full animate-slide-up",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[75%] relative",
          isUser ? "ml-12" : "mr-12"
        )}
      >
        {/* Agent badge for AI messages */}
        {!isUser && message.agent && message.agent !== "unknown" && (
          <div className="mb-1.5">
            <AgentBadge agent={message.agent} />
          </div>
        )}

        {/* Message bubble */}
        <div
          className={cn(
            "px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "rounded-[20px] rounded-br-md bg-accent text-text-on-accent"
              : "rounded-[20px] rounded-bl-md bg-bg-elevated text-text-primary"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="chat-markdown">
              <ReactMarkdown>{message.content}</ReactMarkdown>
              {/* Typing cursor when streaming */}
              {message.isStreaming && (
                <span className="inline-block w-0.5 h-4 bg-text-primary ml-0.5 animate-pulse" />
              )}
            </div>
          )}
        </div>

        {sourceLabel && (
          <div
            className={cn(
              "mt-1 text-[10px] text-text-secondary",
              isUser ? "text-right" : "text-left"
            )}
          >
            {sourceLabel}
          </div>
        )}

        {/* Typing indicator (when AI message is empty and streaming) */}
        {!isUser && message.isStreaming && !message.content && (
          <div className="flex gap-1 px-4 py-3">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        )}
      </div>
    </div>
  );
}
