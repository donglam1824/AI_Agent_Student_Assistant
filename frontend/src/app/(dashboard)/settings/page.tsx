/**
 * Settings page – Theme, account info.
 */

"use client";

import { useTheme } from "next-themes";
import { useAppStore } from "@/lib/store";
import { Sun, Moon, Monitor, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

const THEME_OPTIONS = [
  { value: "dark", icon: Moon, label: "Tối" },
  { value: "light", icon: Sun, label: "Sáng" },
  { value: "system", icon: Monitor, label: "Hệ thống" },
] as const;

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { user, clearAuth } = useAppStore();
  const router = useRouter();

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 animate-fade-in">
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h2 className="text-xl font-semibold text-text-primary">⚙️ Cài đặt</h2>
          <p className="text-sm text-text-secondary mt-1">
            Tùy chỉnh giao diện và quản lý tài khoản
          </p>
        </div>

        {/* Theme selection */}
        <section className="rounded-xl border border-border bg-bg-secondary p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Giao diện
          </h3>
          <div className="grid grid-cols-3 gap-3">
            {THEME_OPTIONS.map(({ value, icon: Icon, label }) => (
              <button
                key={value}
                onClick={() => setTheme(value)}
                className={cn(
                  "flex flex-col items-center gap-2 p-4 rounded-xl",
                  "border transition-all duration-200",
                  theme === value
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border text-text-secondary hover:border-border-hover hover:bg-bg-elevated"
                )}
              >
                <Icon size={22} />
                <span className="text-xs font-medium">{label}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Account */}
        <section className="rounded-xl border border-border bg-bg-secondary p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Tài khoản
          </h3>
          {user ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt=""
                    className="w-10 h-10 rounded-full"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center">
                    <span className="text-sm font-medium text-accent">
                      {user.name?.charAt(0) || user.email.charAt(0)}
                    </span>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {user.name || "Sinh viên"}
                  </p>
                  <p className="text-xs text-text-secondary">{user.email}</p>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-xl text-sm",
                  "border border-error/30 text-error",
                  "hover:bg-error/10 transition-colors duration-150"
                )}
              >
                <LogOut size={14} />
                Đăng xuất
              </button>
            </div>
          ) : (
            <p className="text-sm text-text-secondary">Chưa đăng nhập</p>
          )}
        </section>

        {/* About */}
        <section className="rounded-xl border border-border bg-bg-secondary p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-2">
            Về ORCA
          </h3>
          <p className="text-xs text-text-secondary leading-relaxed">
            ORCA (Orchestrated Research & Campus Assistant) – Ứng dụng Trợ lý AI
            Học tập Đa tác tử cho Sinh viên. Phiên bản 1.0.0
          </p>
        </section>
      </div>
    </div>
  );
}
