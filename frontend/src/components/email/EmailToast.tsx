"use client";

import { useEffect, useState } from "react";
import { EmailSummary } from "@/types";

interface EmailToastProps {
  notifications: EmailSummary[];
  onDismiss: (id: string) => void;
}

export function EmailToast({ notifications, onDismiss }: EmailToastProps) {
  const [visibleToasts, setVisibleToasts] = useState<EmailSummary[]>([]);

  // Tự động dismiss toast sau 6 giây
  useEffect(() => {
    if (notifications.length > visibleToasts.length) {
      const newToasts = notifications.filter(
        (n) => !visibleToasts.find((v) => v.id === n.id)
      );
      
      setVisibleToasts((prev) => [...prev, ...newToasts]);
      
      newToasts.forEach((toast) => {
        setTimeout(() => {
          setVisibleToasts((prev) => prev.filter((t) => t.id !== toast.id));
          onDismiss(toast.id);
        }, 6000);
      });
    }
  }, [notifications, visibleToasts, onDismiss]);

  if (visibleToasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {visibleToasts.map((toast) => (
        <div 
          key={toast.id} 
          className="bg-white dark:bg-gray-800 border-l-4 shadow-lg rounded-r-md p-4 max-w-sm flex flex-col gap-1 transition-all animate-slide-up"
          style={{ 
            borderColor: 
              toast.priority === 'urgent' ? '#ef4444' : 
              toast.priority === 'important' ? '#f59e0b' : 
              toast.priority === 'follow_up' ? '#3b82f6' : '#10b981'
          }}
        >
          <div className="flex justify-between items-start">
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <span>📧 {toast.scan_session === 'morning' ? 'Báo cáo buổi sáng' : 'Email mới'}</span>
              {toast.priority === 'urgent' && <span className="text-red-500 text-xs px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 rounded font-bold">KHẨN</span>}
            </h4>
            <button 
              onClick={() => {
                setVisibleToasts((prev) => prev.filter((t) => t.id !== toast.id));
                onDismiss(toast.id);
              }}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              ✕
            </button>
          </div>
          
          <div className="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">
            <span className="font-medium text-gray-800 dark:text-gray-200">{toast.sender}:</span> {toast.subject}
          </div>
          
          {toast.deadline && (
            <div className="text-xs text-red-600 dark:text-red-400 mt-2 flex items-center gap-1 font-medium bg-red-50 dark:bg-red-900/20 w-fit px-2 py-1 rounded">
              ⚠️ Deadline: {new Date(toast.deadline).toLocaleString('vi-VN')}
            </div>
          )}
          
          <button className="text-xs text-blue-600 dark:text-blue-400 font-medium hover:underline text-left mt-2 w-fit">
            Xem chi tiết →
          </button>
        </div>
      ))}
    </div>
  );
}
