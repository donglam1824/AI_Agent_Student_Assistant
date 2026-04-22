/**
 * components/sidebar/AppSidebar.tsx
 * Main navigation sidebar – collapsible with icon-only mode.
 */

"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  MessageSquare,
  Calendar,
  FileText,
  StickyNote,
  Mail,
  Settings,
  ChevronLeft,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/chat", icon: MessageSquare, label: "Chat AI", id: "nav-chat" },
  { href: "/calendar", icon: Calendar, label: "Lịch học", id: "nav-calendar" },
  { href: "/notes", icon: StickyNote, label: "Ghi chú", id: "nav-notes" },
  { href: "/email", icon: Mail, label: "Email", id: "nav-email" },
  { href: "/docs", icon: FileText, label: "Tài liệu", id: "nav-docs" },
  { href: "/settings", icon: Settings, label: "Cài đặt", id: "nav-settings" },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar, user } = useAppStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-full z-40 flex flex-col",
        "bg-bg-secondary border-r border-border",
        "transition-all duration-300 ease-in-out",
        sidebarOpen ? "w-60" : "w-16"
      )}
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-border">
        <Link href="/chat" className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
            <span className="text-text-on-accent font-bold text-sm">🐋</span>
          </div>
          {sidebarOpen && (
            <span className="text-lg font-bold text-text-primary truncate animate-fade-in">
              ORCA
            </span>
          )}
        </Link>

        {sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="ml-auto p-1.5 rounded-lg hover:bg-bg-elevated transition-colors text-text-secondary"
            aria-label="Thu gọn sidebar"
          >
            <ChevronLeft size={16} />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1">
        {NAV_ITEMS.map(({ href, icon: Icon, label, id }) => {
          const isActive = pathname === href || pathname?.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              id={id}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg",
                "transition-all duration-150 group relative",
                isActive
                  ? "bg-accent/10 text-accent"
                  : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
              )}
            >
              {/* Active indicator bar */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-accent rounded-r" />
              )}
              <Icon size={20} className="flex-shrink-0" />
              {sidebarOpen && (
                <span className="text-sm font-medium truncate animate-fade-in">
                  {label}
                </span>
              )}

              {/* Tooltip when collapsed */}
              {!sidebarOpen && (
                <div
                  className={cn(
                    "absolute left-full ml-2 px-2 py-1 rounded-md text-xs",
                    "bg-bg-elevated text-text-primary border border-border",
                    "opacity-0 group-hover:opacity-100 pointer-events-none",
                    "transition-opacity duration-150 whitespace-nowrap",
                    "shadow-md"
                  )}
                >
                  {label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      {user && sidebarOpen && (
        <div className="p-3 border-t border-border animate-fade-in">
          <div className="flex items-center gap-2 px-2">
            {user.picture ? (
              <img
                src={user.picture}
                alt=""
                className="w-7 h-7 rounded-full flex-shrink-0"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-medium text-accent">
                  {user.name?.charAt(0) || user.email.charAt(0)}
                </span>
              </div>
            )}
            <div className="min-w-0">
              <p className="text-xs font-medium text-text-primary truncate">
                {user.name || "Sinh viên"}
              </p>
              <p className="text-[10px] text-text-secondary truncate">
                {user.email}
              </p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
