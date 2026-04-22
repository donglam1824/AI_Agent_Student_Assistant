/**
 * Email page – Gmail inbox viewer + compose dialog.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { getEmailInbox, sendEmail } from "@/lib/api";
import {
  Mail,
  Send,
  RefreshCw,
  Plus,
  X,
  MessageSquare,
  Inbox,
  ChevronRight,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import type { EmailItem } from "@/types";

export default function EmailPage() {
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCompose, setShowCompose] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<EmailItem | null>(null);
  const [sending, setSending] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  // Compose form
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");

  const fetchEmails = useCallback(async () => {
    try {
      const data = await getEmailInbox(15);
      setEmails(data);
    } catch {
      setEmails([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEmails();
  }, [fetchEmails]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchEmails();
    setRefreshing(false);
  };

  const handleSend = async () => {
    if (!to.trim() || !subject.trim()) return;
    setSending(true);
    try {
      await sendEmail({
        subject: subject.trim(),
        body: body.trim(),
        to_recipients: to.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setTo("");
      setSubject("");
      setBody("");
      setShowCompose(false);
      // Refresh inbox after sending
      fetchEmails();
    } catch (e) {
      console.error(e);
      alert("Lỗi khi gửi email. Vui lòng thử lại.");
    } finally {
      setSending(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const isToday = d.toDateString() === now.toDateString();
      if (isToday) {
        return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
      }
      return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
    } catch {
      return dateStr;
    }
  };

  // Extract sender name from email format "Name <email@example.com>"
  const parseSender = (sender: string) => {
    const match = sender.match(/^(.+?)\s*<.+>$/);
    return match ? match[1].replace(/"/g, "") : sender;
  };

  return (
    <div className="flex-1 overflow-hidden flex flex-col animate-fade-in">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-xl font-semibold text-text-primary">
            📧 Email học thuật
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Quản lý email từ giảng viên và nhà trường
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push("/chat")}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
              "bg-bg-elevated text-text-secondary",
              "hover:bg-bg-secondary hover:text-text-primary transition-colors"
            )}
          >
            <MessageSquare size={16} />
            Nhờ AI soạn email
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={cn(
              "p-2 rounded-xl text-text-secondary",
              "hover:bg-bg-elevated transition-colors",
              refreshing && "animate-spin text-accent"
            )}
            title="Làm mới"
          >
            <RefreshCw size={18} />
          </button>
          <button
            onClick={() => setShowCompose(true)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
              "bg-accent text-text-on-accent",
              "hover:bg-accent-hover transition-colors duration-150"
            )}
          >
            <Plus size={16} />
            Soạn email
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Email list */}
        <div className={cn(
          "overflow-y-auto border-r border-border transition-all",
          selectedEmail ? "w-1/3" : "w-full"
        )}>
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-text-secondary">Đang tải email...</p>
              </div>
            </div>
          ) : emails.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center px-6">
              <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-4">
                <Inbox size={28} className="text-accent" />
              </div>
              <h3 className="text-lg font-medium text-text-primary mb-2">
                Hộp thư trống
              </h3>
              <p className="text-sm text-text-secondary max-w-sm">
                Chưa có email nào hoặc chưa kết nối Gmail. Hãy thử soạn email mới.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {emails.map((email, idx) => (
                <button
                  key={email.id}
                  onClick={() => setSelectedEmail(email)}
                  className={cn(
                    "w-full text-left px-5 py-4 flex items-start gap-3",
                    "hover:bg-bg-elevated transition-colors",
                    "animate-slide-up group",
                    selectedEmail?.id === email.id && "bg-accent/5 border-l-2 border-l-accent"
                  )}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  {/* Avatar */}
                  <div className="w-9 h-9 rounded-full bg-accent/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-semibold text-accent">
                      {parseSender(email.sender).charAt(0).toUpperCase()}
                    </span>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {parseSender(email.sender)}
                      </p>
                      <span className="text-[11px] text-text-secondary/70 flex-shrink-0 ml-2">
                        {formatDate(email.received_date_time)}
                      </span>
                    </div>
                    <p className="text-sm text-text-primary truncate font-medium">
                      {email.subject}
                    </p>
                    <p className="text-xs text-text-secondary truncate mt-0.5">
                      {email.body_preview}
                    </p>
                  </div>

                  <ChevronRight
                    size={14}
                    className="text-text-secondary/40 flex-shrink-0 mt-2 opacity-0 group-hover:opacity-100 transition-opacity"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Email detail panel */}
        {selectedEmail && (
          <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
            <div className="max-w-2xl">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-lg font-semibold text-text-primary">
                  {selectedEmail.subject}
                </h3>
                <button
                  onClick={() => setSelectedEmail(null)}
                  className="p-1.5 rounded-lg text-text-secondary hover:bg-bg-elevated transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full bg-accent/15 flex items-center justify-center">
                  <span className="text-sm font-semibold text-accent">
                    {parseSender(selectedEmail.sender).charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {parseSender(selectedEmail.sender)}
                  </p>
                  <p className="text-xs text-text-secondary">
                    {selectedEmail.received_date_time}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-bg-secondary p-5">
                <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
                  {selectedEmail.body_preview}
                </p>
                <p className="text-xs text-text-secondary/60 mt-4 italic">
                  (Hiển thị xem trước – nội dung đầy đủ cần tích hợp thêm)
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Compose modal */}
      {showCompose && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-bg-primary border border-border shadow-[var(--shadow-lg)] animate-scale-in">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <Mail size={16} className="text-accent" />
                Soạn email mới
              </h3>
              <button
                onClick={() => setShowCompose(false)}
                className="p-1.5 rounded-lg text-text-secondary hover:bg-bg-elevated transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <div className="p-5 space-y-3">
              <input
                type="text"
                placeholder="Đến (email, phân cách bằng dấu phẩy)"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                className={cn(
                  "w-full px-4 py-2.5 rounded-lg text-sm",
                  "bg-bg-secondary border border-border",
                  "text-text-primary placeholder:text-text-secondary/60",
                  "focus:outline-none focus:border-accent"
                )}
                autoFocus
              />
              <input
                type="text"
                placeholder="Tiêu đề"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className={cn(
                  "w-full px-4 py-2.5 rounded-lg text-sm",
                  "bg-bg-secondary border border-border",
                  "text-text-primary placeholder:text-text-secondary/60",
                  "focus:outline-none focus:border-accent"
                )}
              />
              <textarea
                placeholder="Nội dung email..."
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={8}
                className={cn(
                  "w-full px-4 py-2.5 rounded-lg text-sm resize-none",
                  "bg-bg-secondary border border-border",
                  "text-text-primary placeholder:text-text-secondary/60",
                  "focus:outline-none focus:border-accent"
                )}
              />
            </div>

            <div className="flex justify-end gap-2 p-5 border-t border-border">
              <button
                onClick={() => setShowCompose(false)}
                className="px-4 py-2 rounded-lg text-sm text-text-secondary hover:bg-bg-elevated transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={handleSend}
                disabled={!to.trim() || !subject.trim() || sending}
                className={cn(
                  "flex items-center gap-2 px-5 py-2 rounded-lg text-sm",
                  "bg-accent text-text-on-accent",
                  "hover:bg-accent-hover transition-colors",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <Send size={14} />
                {sending ? "Đang gửi..." : "Gửi email"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
