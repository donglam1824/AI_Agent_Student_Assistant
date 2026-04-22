/**
 * hooks/useChat.ts
 * Custom hook for chat with SSE streaming from FastAPI.
 */

"use client";

import { useState, useCallback, useRef } from "react";
import { sendChatMessage } from "@/lib/api";
import { tempId } from "@/lib/utils";
import type { ChatMessage, AgentType } from "@/types";

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  currentAgent: AgentType | null;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  clearMessages: () => void;
}

export function useChat(chatId: string | null): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<AgentType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chatIdRef = useRef(chatId);
  chatIdRef.current = chatId;

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      setError(null);
      setIsLoading(true);
      setCurrentAgent(null);

      // Add user message immediately (optimistic)
      const userMsg: ChatMessage = {
        id: tempId(),
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // Add placeholder for AI response
      const aiMsgId = tempId();
      const aiMsg: ChatMessage = {
        id: aiMsgId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, aiMsg]);

      try {
        const response = await sendChatMessage(text, chatIdRef.current);

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

          // Parse SSE events from buffer
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

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
                  // Update the AI message with agent info
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === aiMsgId ? { ...m, agent: data.agent } : m
                    )
                  );
                } else if (eventType === "token") {
                  // Append content to AI message
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === aiMsgId
                        ? { ...m, content: m.content + data.content }
                        : m
                    )
                  );
                } else if (eventType === "done") {
                  // Mark streaming as complete
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === aiMsgId ? { ...m, isStreaming: false } : m
                    )
                  );
                  // Update chatId if this was a new chat
                  if (data.chat_id) {
                    chatIdRef.current = data.chat_id;
                  }
                } else if (eventType === "error") {
                  setError(data.message);
                }
              } catch {
                // Skip malformed JSON
              }
            }
          }
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Đã xảy ra lỗi kết nối";
        setError(message);
        // Remove the empty AI message on error
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
