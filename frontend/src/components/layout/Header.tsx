/**
 * components/layout/Header.tsx
 * Minimal header with page title, theme toggle, and user menu.
 */

"use client";

import { Menu, LogOut } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title?: string;
}

export function Header({ title = "ORCA" }: HeaderProps) {
  const { user, clearAuth, toggleSidebar } = useAppStore();

  return (
    <header
      className={cn(
        "h-14 flex items-center justify-between px-4",
        "border-b border-border bg-bg-primary",
        "sticky top-0 z-30"
      )}
    >
      {/* Left: Hamburger + Title */}
      <div className="flex items-center gap-3">
        <button
          id="sidebar-toggle"
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-secondary hover:text-text-primary"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-base font-semibold text-text-primary">{title}</h1>
      </div>

      {/* Right: Theme toggle + User */}
      <div className="flex items-center gap-2">
        <ThemeToggle />

        {user && (
          <div className="flex items-center gap-2 ml-2">
            {user.picture ? (
              <img
                src={user.picture}
                alt={user.name || ""}
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center text-text-on-accent text-sm font-medium">
                {user.name?.charAt(0) || user.email.charAt(0)}
              </div>
            )}
            <button
              onClick={clearAuth}
              className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-text-secondary hover:text-error"
              aria-label="Đăng xuất"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
