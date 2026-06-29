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
    // Chỉ kết nối khi có token (đã đăng nhập)
    const token = localStorage.getItem("orca_token");
    if (!token) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: NodeJS.Timeout;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;

    const connectSSE = () => {
      // Truyền token qua query params do EventSource không gửi được Authorization header
      const sseUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/email/notifications/stream?token=${token}`;
      
      eventSource = new EventSource(sseUrl);

      eventSource.onopen = () => {
        reconnectAttempts = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const newEmail: EmailSummary = JSON.parse(event.data);
          
          setNotifications((prev) => {
            // Tránh trùng lặp
            if (prev.find(n => n.id === newEmail.id)) return prev;
            return [newEmail, ...prev];
          });
          
          setUnreadCount((prev) => prev + 1);
          
        } catch (error) {
          console.error("Error parsing SSE data", error);
        }
      };

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
        }

        reconnectAttempts++;
        if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(2000 * Math.pow(2, reconnectAttempts - 1), 32000);
          console.warn(
            `SSE disconnected. Reconnecting in ${delay / 1000}s (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`
          );
          reconnectTimeout = setTimeout(connectSSE, delay);
        } else {
          console.warn("SSE: Max reconnect attempts reached. Stopping.");
        }
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
