/**
 * Dashboard layout – Sidebar + Header + Main content area.
 */

"use client";

import { AppSidebar } from "@/components/sidebar/AppSidebar";
import { Header } from "@/components/layout/Header";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { sidebarOpen } = useAppStore();

  return (
    <div className="h-screen flex overflow-hidden bg-bg-primary">
      {/* Sidebar */}
      <AppSidebar />

      {/* Main area */}
      <div
        className={cn(
          "flex-1 flex flex-col min-w-0",
          "transition-all duration-300",
          sidebarOpen ? "ml-60" : "ml-16"
        )}
      >
        <Header />
        <main className="flex-1 overflow-hidden flex flex-col">
          {children}
        </main>
      </div>
    </div>
  );
}
