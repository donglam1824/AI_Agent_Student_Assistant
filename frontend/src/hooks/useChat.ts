/** Custom hook kết nối chat SSE streaming từ FastAPI */

"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { sendChatMessage } from "@/lib/api";
import { tempId } from "@/lib/utils";
import type { ChatMessage, AgentType, ChatSourceScope } from "@/types";

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  currentAgent: AgentType | null;
  error: string | null;
  sendMessage: (text: string, sourceScope?: ChatSourceScope | null) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  clearMessages: () => void;
}

export function useChat(chatId: string | null): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<AgentType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chatIdRef = useRef(chatId);

  useEffect(() => {
    chatIdRef.current = chatId;
  }, [chatId]);

  const sendMessage = useCallback(
    async (text: string, sourceScope?: ChatSourceScope | null) => {
      if (!text.trim() || isLoading) return;

      setError(null);
      setIsLoading(true);
      setCurrentAgent(null);

      // Hiển thị tin nhắn user ngay (optimistic update)
      const userMsg: ChatMessage = {
        id: tempId(),
        role: "user",
        content: text,
        source_scope: sourceScope?.mode === "all" ? null : sourceScope,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // Chờ tin nhắn từ AI
      const aiMsgId = tempId();
      const aiMsg: ChatMessage = {
        id: aiMsgId,
        role: "assistant",
        content: "",
        source_scope: sourceScope?.mode === "all" ? null : sourceScope,
        created_at: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, aiMsg]);

      try {
        const response = await sendChatMessage(text, chatIdRef.current, sourceScope);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse sự kiện SSE từ buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const dataStr = line.slice(6);
              try {
                const data = JSON.parse(dataStr);

                if (eventType === "agent") {
                  setCurrentAgent(data.agent as AgentType);
                  // Cập nhật thông tin Agent vào tin nhắn
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === aiMsgId ? { ...m, agent: data.agent } : m
                    )
                  );
                } else if (eventType === "token") {
                  // Thêm nội dung stream vào tin nhắn
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === aiMsgId
                        ? { ...m, content: m.content + data.content }
                        : m
                    )
                  );
                } else if (eventType === "done") {
                  // Hoàn thành stream
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === aiMsgId ? { ...m, isStreaming: false } : m
                    )
                  );
                  // Lưu chatId nếu là chat mới
                  if (data.chat_id) {
                    chatIdRef.current = data.chat_id;
                  }
                } else if (eventType === "error") {
                  setError(data.message);
                }
              } catch {
              }
            }
          }
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Đã xảy ra lỗi kết nối";
        setError(message);
        // Báo lỗi vào tin nhắn AI
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiMsgId
              ? {
                  ...m,
                  content: `❌ Lỗi: ${message}`,
                  isStreaming: false,
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        setCurrentAgent(null);
      }
    },
    [isLoading]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    setCurrentAgent(null);
  }, []);

  return {
    messages,
    isLoading,
    currentAgent,
    error,
    sendMessage,
    setMessages,
    clearMessages,
  };
}
