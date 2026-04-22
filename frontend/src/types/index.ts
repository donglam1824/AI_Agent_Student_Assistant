/**
 * types/index.ts
 * TypeScript interfaces for ORCA frontend.
 */

// ── Auth ──────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string | null;
  picture: string | null;
}

// ── Chat ──────────────────────────────────────────────────────────────────

export type AgentType = "calendar" | "note" | "email" | "docsearch" | "unknown";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: AgentType | null;
  created_at: string;
  isStreaming?: boolean;
}

export interface ChatSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

// ── Documents ─────────────────────────────────────────────────────────────

export type DocumentStatus = "processing" | "ready" | "error";

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: DocumentStatus;
  error_message?: string | null;
  created_at: string;
}

// ── Calendar ──────────────────────────────────────────────────────────────

export interface CalendarEvent {
  id: string;
  summary: string;
  start: string;
  end: string;
  location?: string | null;
  description?: string | null;
}

// ── Notes ─────────────────────────────────────────────────────────────────

export interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

// ── Email ─────────────────────────────────────────────────────────────────

export interface EmailItem {
  id: string;
  subject: string;
  sender: string;
  body_preview: string;
  received_date_time: string;
}

