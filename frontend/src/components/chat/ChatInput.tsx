/**
 * components/chat/ChatInput.tsx
 * Chat input bar with auto-resize textarea and send button.
 */

"use client";

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { Send, Paperclip } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload?: (file: File) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onFileUpload,
  disabled = false,
  placeholder = "Nhập tin nhắn...",
}: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSend = useCallback(() => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`; // Max ~4 lines
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onFileUpload) {
      onFileUpload(file);
    }
    e.target.value = "";
  };

  return (
    <div
      className={cn(
        "flex items-end gap-2 p-3",
        "border-t border-border bg-bg-primary"
      )}
    >
      {/* File upload button */}
      {onFileUpload && (
        <>
          <button
            id="chat-upload-btn"
            onClick={handleFileClick}
            className={cn(
              "p-2.5 rounded-xl flex-shrink-0",
              "text-text-secondary hover:text-text-primary hover:bg-bg-elevated",
              "transition-colors duration-150"
            )}
            aria-label="Đính kèm file"
          >
            <Paperclip size={18} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
        </>
      )}

      {/* Textarea */}
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          id="chat-input"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className={cn(
            "w-full resize-none px-4 py-2.5 rounded-xl",
            "bg-bg-secondary border border-border",
            "text-sm text-text-primary placeholder:text-text-secondary",
            "focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30",
            "transition-all duration-150",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
      </div>

      {/* Send button */}
      <button
        id="chat-send-btn"
        onClick={handleSend}
        disabled={!text.trim() || disabled}
        className={cn(
          "p-2.5 rounded-xl flex-shrink-0",
          "transition-all duration-150",
          text.trim() && !disabled
            ? "bg-accent text-text-on-accent hover:bg-accent-hover shadow-sm"
            : "bg-bg-elevated text-text-secondary cursor-not-allowed"
        )}
        aria-label="Gửi tin nhắn"
      >
        <Send size={18} />
      </button>
    </div>
  );
}
