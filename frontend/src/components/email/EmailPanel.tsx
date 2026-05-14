"use client";

import { useEffect, useState } from "react";
import { EmailSummary } from "@/types";

interface EmailPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function EmailPanel({ isOpen, onClose }: EmailPanelProps) {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchEmails();
    }
  }, [isOpen]);

  const fetchEmails = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/email/summaries?limit=20", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`
        }
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
  };

  if (!isOpen) return null;

  const urgent = emails.filter(e => e.priority === 'urgent');
  const important = emails.filter(e => e.priority === 'important');
  const followUp = emails.filter(e => e.priority === 'follow_up');
  const info = emails.filter(e => e.priority === 'info' || !e.priority);

  const PrioritySection = ({ title, items, colorClass }: { title: string, items: EmailSummary[], colorClass: string }) => {
    if (items.length === 0) return null;
    return (
      <div className="mb-6">
        <h4 className={`text-xs font-bold uppercase tracking-wider mb-3 flex items-center gap-2 ${colorClass}`}>
          {title} ({items.length})
        </h4>
        <div className="flex flex-col gap-3">
          {items.map(email => (
            <div key={email.id} className="bg-white dark:bg-gray-800 p-3 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-1">
                <span className="font-semibold text-sm text-gray-900 dark:text-gray-100 line-clamp-1 flex-1 pr-2">
                  {email.sender}
                </span>
                <span className="text-xs text-gray-500 whitespace-nowrap">
                  {email.received_at ? new Date(email.received_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'}) : ''}
                </span>
              </div>
              <div className="text-sm text-gray-700 dark:text-gray-300 font-medium mb-1 line-clamp-1">
                {email.subject}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-2 line-clamp-2">
                {email.summary}
              </div>
              
              {email.deadline && (
                <div className="mt-2 text-xs font-medium text-red-600 bg-red-50 dark:bg-red-900/20 px-2 py-1.5 rounded inline-flex items-center gap-1 w-full">
                  ⚠️ Deadline: {new Date(email.deadline).toLocaleString('vi-VN')}
                </div>
              )}
              
              <div className="flex gap-2 mt-3">
                <button className="text-xs font-medium px-3 py-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-gray-700 dark:text-gray-200 transition-colors">
                  Xem chi tiết
                </button>
                {email.requires_reply && (
                  <button className="text-xs font-medium px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded transition-colors">
                    Trả lời
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      <div 
        className="fixed inset-0 bg-black/20 dark:bg-black/40 z-40" 
        onClick={onClose}
      />
      <div className="fixed right-0 top-0 bottom-0 w-[400px] max-w-[90vw] bg-gray-50 dark:bg-gray-900 z-50 shadow-2xl flex flex-col border-l border-gray-200 dark:border-gray-800 animate-slide-left">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <span>📧</span> Email
          </h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors"
          >
            ✕
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex justify-center items-center h-40">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : emails.length === 0 ? (
            <div className="text-center text-gray-500 dark:text-gray-400 mt-10">
              Không có email nào gần đây.
            </div>
          ) : (
            <>
              <PrioritySection title="🔴 Khẩn Cấp" items={urgent} colorClass="text-red-600 dark:text-red-400" />
              <PrioritySection title="🟠 Quan Trọng" items={important} colorClass="text-amber-600 dark:text-amber-500" />
              <PrioritySection title="🔵 Cần Phản Hồi" items={followUp} colorClass="text-blue-600 dark:text-blue-400" />
              <PrioritySection title="🟢 Thông Tin" items={info} colorClass="text-emerald-600 dark:text-emerald-500" />
            </>
          )}
        </div>
        
        <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <button 
            className="w-full py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
            onClick={() => window.location.href = '/email'}
          >
            Xem tất cả email →
          </button>
        </div>
      </div>
    </>
  );
}
