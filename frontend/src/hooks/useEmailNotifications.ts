import { useState, useEffect } from 'react';
import { EmailSummary } from '@/types';

interface UseEmailNotificationsResult {
  notifications: EmailSummary[];
  unreadCount: number;
  clearNotification: (id: string) => void;
  clearAll: () => void;
}

export function useEmailNotifications(): UseEmailNotificationsResult {
  const [notifications, setNotifications] = useState<EmailSummary[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    // Chỉ kết nối khi có token trong localStorage (đã đăng nhập)
    const token = localStorage.getItem("token");
    if (!token) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connectSSE = () => {
      // Vì EventSource mặc định không gửi headers custom (như Authorization),
      // nên trong thực tế cần pass token qua query params, hoặc dùng custom fetch (ví dụ fetch-event-source)
      // Ở đây ta mô phỏng kết nối SSE với url backend (nếu BE config cookie auth)
      const sseUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/email/notifications/stream?token=${token}`;
      
      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        try {
          const newEmail: EmailSummary = JSON.parse(event.data);
          
          setNotifications((prev) => {
            // Tránh duplicate
            if (prev.find(n => n.id === newEmail.id)) return prev;
            return [newEmail, ...prev];
          });
          
          setUnreadCount((prev) => prev + 1);
          
        } catch (error) {
          console.error("Error parsing SSE data", error);
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE error, attempting to reconnect...", error);
        if (eventSource) {
          eventSource.close();
        }
        // Thử kết nối lại sau 5 giây
        reconnectTimeout = setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, []);

  const clearNotification = (id: string) => {
    setNotifications((prev) => prev.filter(n => n.id !== id));
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const clearAll = () => {
    setNotifications([]);
    setUnreadCount(0);
  };

  return { notifications, unreadCount, clearNotification, clearAll };
}
