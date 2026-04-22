/**
 * components/docs/DropZone.tsx
 * Drag & drop file upload area for RAG documents.
 */

"use client";

import { useState, useRef, useCallback, DragEvent } from "react";
import { Upload, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface DropZoneProps {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
];
const ACCEPTED_EXTENSIONS = ".pdf,.docx,.txt";

export function DropZone({ onUpload, disabled = false }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file && isValidFile(file)) {
        onUpload(file);
      }
    },
    [disabled, onUpload]
  );

  const handleClick = () => {
    if (!disabled) fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = "";
  };

  return (
    <div
      id="doc-dropzone"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
      className={cn(
        "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer",
        "transition-all duration-200",
        isDragging
          ? "border-accent bg-accent/5 scale-[1.01]"
          : "border-border hover:border-accent/40 hover:bg-bg-elevated/50",
        disabled && "opacity-50 cursor-not-allowed"
      )}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        onChange={handleFileChange}
        className="hidden"
      />

      <div className="flex flex-col items-center gap-3">
        <div
          className={cn(
            "w-12 h-12 rounded-xl flex items-center justify-center",
            "transition-colors duration-200",
            isDragging ? "bg-accent/20 text-accent" : "bg-bg-elevated text-text-secondary"
          )}
        >
          {isDragging ? <FileText size={24} /> : <Upload size={24} />}
        </div>

        <div>
          <p className="text-sm font-medium text-text-primary">
            {isDragging ? "Thả file vào đây" : "Kéo thả file hoặc nhấn để chọn"}
          </p>
          <p className="text-xs text-text-secondary mt-1">
            Hỗ trợ: PDF, DOCX, TXT
          </p>
        </div>
      </div>
    </div>
  );
}

function isValidFile(file: File): boolean {
  const ext = file.name.split(".").pop()?.toLowerCase();
  return ["pdf", "docx", "txt"].includes(ext || "");
}
