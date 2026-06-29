/** Giao diện chính của dashboard gồm Sidebar, Header và Content */

"use client";

import { AppSidebar } from "@/components/sidebar/AppSidebar";
import { Header } from "@/components/layout/Header";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { sidebarOpen, token, user, restoreSession } = useAppStore();
  const router = useRouter();
  const [isMounting, setIsMounting] = useState(true);

  useEffect(() => {
    restoreSession().finally(() => setIsMounting(false));
  }, [restoreSession]);

  useEffect(() => {
    if (!isMounting && !token) {
      router.push("/login");
    }
  }, [isMounting, token, router]);

  if (isMounting || (token && !user)) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-bg-primary">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-accent" />
      </div>
    );
  }

  if (!token) {
    return null;
  }

  return (
    <div className="h-screen flex overflow-hidden bg-bg-primary">
      <AppSidebar />
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
