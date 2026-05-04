"use client";

import { useState } from "react";
import { Mail } from "lucide-react";
import { useEmailNotifications } from "@/hooks/useEmailNotifications";
import { EmailToast } from "./EmailToast";
import { EmailPanel } from "./EmailPanel";

interface EmailNotificationBadgeProps {
  sidebarOpen: boolean;
  isActive: boolean;
}

export function EmailNotificationBadge({ sidebarOpen, isActive }: EmailNotificationBadgeProps) {
  const { notifications, unreadCount, clearNotification } = useEmailNotifications();
  const [panelOpen, setPanelOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setPanelOpen(true)}
        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group relative
          ${isActive ? "bg-accent/10 text-accent" : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary"}`}
      >
        {isActive && (
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r" />
        )}
        
        <div className="relative flex-shrink-0">
          <Mail size={20} />
          {unreadCount > 0 && (
            <span className="absolute -top-1.5 -right-1.5 bg-red-500 text-white text-[10px] font-bold px-1 min-w-[16px] h-[16px] rounded-full flex items-center justify-center animate-pulse-soft">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </div>

        {sidebarOpen && (
          <span className="text-sm font-medium truncate animate-fade-in flex-1 text-left">
            Email
          </span>
        )}

        {!sidebarOpen && (
          <div className="absolute left-full ml-2 px-2 py-1 rounded-md text-xs bg-bg-elevated text-text-primary border border-border opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 whitespace-nowrap shadow-md z-50">
            Email {unreadCount > 0 ? `(${unreadCount} mới)` : ''}
          </div>
        )}
      </button>

      {/* Render Toast globally */}
      <EmailToast notifications={notifications} onDismiss={clearNotification} />
      
      {/* Render Panel */}
      <EmailPanel isOpen={panelOpen} onClose={() => setPanelOpen(false)} />
    </>
  );
}
