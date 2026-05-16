"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  ExternalLink,
  Info,
  Mail,
  Reply,
  X,
} from "lucide-react";
import { EmailSummary } from "@/types";
import { cn } from "@/lib/utils";

interface EmailPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const priorityMeta = {
  urgent: {
    icon: AlertTriangle,
    label: "Khẩn cấp",
    colorClass: "text-error",
  },
  important: {
    icon: Clock,
    label: "Quan trọng",
    colorClass: "text-warning",
  },
  follow_up: {
    icon: Reply,
    label: "Cần phản hồi",
    colorClass: "text-accent",
  },
  info: {
    icon: Info,
    label: "Thông tin",
    colorClass: "text-success",
  },
};

interface PrioritySectionProps {
  items: EmailSummary[];
  type: keyof typeof priorityMeta;
}

function PrioritySection({ items, type }: PrioritySectionProps) {
  if (items.length === 0) return null;

  const { icon: Icon, label, colorClass } = priorityMeta[type];

  return (
    <section className="mb-6 last:mb-0">
      <h4
        className={cn(
          "mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide",
          colorClass
        )}
      >
        <Icon size={14} />
        <span>
          {label} ({items.length})
        </span>
      </h4>

      <div className="flex flex-col gap-3">
        {items.map((email) => (
          <article
            key={email.id}
            className="rounded-lg border border-border bg-bg-primary p-3 shadow-sm transition-colors hover:border-border-hover hover:bg-bg-elevated/60"
          >
            <div className="mb-1 flex items-start justify-between gap-3">
              <span className="min-w-0 flex-1 truncate text-sm font-semibold text-text-primary">
                {email.sender}
              </span>
              <span className="shrink-0 text-xs text-text-secondary">
                {email.received_at
                  ? new Date(email.received_at).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : ""}
              </span>
            </div>

            <div className="mb-1 line-clamp-1 text-sm font-medium text-text-primary">
              {email.subject}
            </div>
            <div className="mb-2 line-clamp-2 text-xs leading-5 text-text-secondary">
              {email.summary || "Chưa có tóm tắt."}
            </div>

            {email.deadline && (
              <div className="mt-2 flex w-full items-center gap-1.5 rounded-md border border-red-500/20 bg-red-500/10 px-2 py-1.5 text-xs font-medium text-error">
                <AlertTriangle size={13} />
                <span>Deadline: {new Date(email.deadline).toLocaleString("vi-VN")}</span>
              </div>
            )}

            <div className="mt-3 flex gap-2">
              <button className="inline-flex items-center gap-1.5 rounded-md bg-bg-elevated px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-accent-light hover:text-accent">
                <ExternalLink size={13} />
                Xem chi tiết
              </button>
              {email.requires_reply && (
                <button className="inline-flex items-center gap-1.5 rounded-md bg-accent-light px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20">
                  <Reply size={13} />
                  Trả lời
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function EmailPanel({ isOpen, onClose }: EmailPanelProps) {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchEmails = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/email/summaries?limit=20", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setEmails(data);
      }
    } catch (error) {
      console.error("Error fetching email summaries:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      queueMicrotask(() => {
        void fetchEmails();
      });
    }
  }, [fetchEmails, isOpen]);

  if (!isOpen) return null;

  const urgent = emails.filter((email) => email.priority === "urgent");
  const important = emails.filter((email) => email.priority === "important");
  const followUp = emails.filter((email) => email.priority === "follow_up");
  const info = emails.filter((email) => email.priority === "info" || !email.priority);

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/45 backdrop-blur-[1px]"
        onClick={onClose}
      />
      <aside className="fixed bottom-0 right-0 top-0 z-50 flex w-[400px] max-w-[90vw] min-h-0 flex-col border-l border-border bg-bg-secondary shadow-2xl animate-slide-in-right">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-bg-primary/95 px-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-text-primary">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-light text-accent">
              <Mail size={17} />
            </span>
            Email
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng email"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary transition-colors hover:bg-bg-elevated hover:text-text-primary"
          >
            <X size={18} />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" />
            </div>
          ) : emails.length === 0 ? (
            <div className="flex h-full min-h-[220px] items-center justify-center text-center text-sm font-medium text-text-secondary">
              Không có email nào gần đây.
            </div>
          ) : (
            <>
              <PrioritySection type="urgent" items={urgent} />
              <PrioritySection type="important" items={important} />
              <PrioritySection type="follow_up" items={followUp} />
              <PrioritySection type="info" items={info} />
            </>
          )}
        </div>

        <footer className="shrink-0 border-t border-border bg-bg-primary/95 p-4">
          <button
            type="button"
            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-accent-light px-3 py-2 text-sm font-semibold text-accent transition-colors hover:bg-accent/20"
            onClick={() => window.location.assign("/email")}
          >
            Xem tất cả email
            <ArrowRight size={15} />
          </button>
        </footer>
      </aside>
    </>
  );
}
