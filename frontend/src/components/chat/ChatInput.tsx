/**
 * components/chat/ChatInput.tsx
 * Chat input bar with auto-resize textarea and send button.
 */

"use client";

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { BookOpen, Send, Upload } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload?: (file: File) => void;
  onOpenSourcePicker?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  onFileUpload,
  onOpenSourcePicker,
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
        "flex items-end gap-2 px-4 py-3",
        "border-t border-border bg-bg-primary"
      )}
    >
      {/* Upload button */}
      {onFileUpload && (
        <>
          <button
            id="chat-upload-btn"
            onClick={handleFileClick}
            disabled={disabled}
            className={cn(
              "h-12 w-12 rounded-xl flex-shrink-0 inline-flex items-center justify-center",
              "text-text-secondary hover:text-text-primary hover:bg-bg-elevated",
              "transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            )}
            aria-label="Tải lên tài liệu"
            title="Tải lên tài liệu"
          >
            <Upload size={18} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.pptx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />
        </>
      )}

      {onOpenSourcePicker && (
        <button
          id="chat-source-btn"
          onClick={onOpenSourcePicker}
          disabled={disabled}
          className={cn(
            "h-12 w-12 rounded-xl flex-shrink-0 inline-flex items-center justify-center",
            "text-text-secondary hover:text-text-primary hover:bg-bg-elevated",
            "transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          )}
          aria-label="Sử dụng tài liệu"
          title="Sử dụng tài liệu"
        >
          <BookOpen size={18} />
        </button>
      )}

      {/* Textarea */}
      <div className="flex-1 min-w-0 relative">
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
            "block min-h-12 w-full resize-none overflow-hidden px-4 py-3 rounded-xl leading-5",
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
          "h-12 w-12 rounded-xl flex-shrink-0 inline-flex items-center justify-center",
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
