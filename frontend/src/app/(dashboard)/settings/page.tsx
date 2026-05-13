/**
 * Settings page – Theme, account info.
 */

"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { useAppStore } from "@/lib/store";
import { CheckCircle2, Loader2, Moon, Monitor, PlugZap, Sun, Unplug, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { disconnectMicrosoft, getConnections, getMicrosoftAuthUrl } from "@/lib/api";
import type { ConnectionStatus } from "@/types";

const THEME_OPTIONS = [
  { value: "dark", icon: Moon, label: "Tối" },
  { value: "light", icon: Sun, label: "Sáng" },
  { value: "system", icon: Monitor, label: "Hệ thống" },
] as const;

function getErrorMessage(err: unknown, fallback: string) {
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail) return response.data.detail;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const { user, clearAuth } = useAppStore();
  const router = useRouter();
  const [connections, setConnections] = useState<ConnectionStatus | null>(null);
  const [connectionLoading, setConnectionLoading] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const loadConnections = async () => {
    try {
      setConnectionError(null);
      setConnections(await getConnections());
    } catch (err: unknown) {
      setConnectionError(getErrorMessage(err, "Khong tai duoc trang thai ket noi."));
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadConnections();
  }, []);

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  const handleConnectMicrosoft = async () => {
    try {
      setConnectionLoading(true);
      setConnectionError(null);
      const redirectUri = `${window.location.origin}/auth/microsoft/callback`;
      const data = await getMicrosoftAuthUrl(redirectUri);
      window.location.href = data.auth_url;
    } catch (err: unknown) {
      setConnectionError(getErrorMessage(err, "Khong tao duoc URL dang nhap Microsoft."));
      setConnectionLoading(false);
    }
  };

  const handleDisconnectMicrosoft = async () => {
    try {
      setConnectionLoading(true);
      setConnectionError(null);
      await disconnectMicrosoft();
      await loadConnections();
    } catch (err: unknown) {
      setConnectionError(getErrorMessage(err, "Khong ngat duoc ket noi Microsoft."));
    } finally {
      setConnectionLoading(false);
    }
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

        <section className="rounded-xl border border-border bg-bg-secondary p-5">
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Ket noi dich vu
          </h3>
          {connectionError && (
            <div className="mb-3 rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-xs text-error">
              {connectionError}
            </div>
          )}
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg border border-border bg-bg-primary p-4">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-text-primary">Google</p>
                  {connections?.google_connected && (
                    <CheckCircle2 size={15} className="text-green-500" />
                  )}
                </div>
                <p className="text-xs text-text-secondary">
                  Gmail, Calendar va Drive dang dung qua dang nhap Google.
                </p>
              </div>
              <span className="text-xs text-text-secondary">
                {connections?.google_connected ? "Da ket noi" : "Chua ket noi"}
              </span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-bg-primary p-4">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-text-primary">Microsoft</p>
                  {connections?.microsoft_connected && (
                    <CheckCircle2 size={15} className="text-green-500" />
                  )}
                </div>
                <p className="text-xs text-text-secondary">
                  Outlook, Teams, tin nhan lop va bai tap.
                </p>
                {connections?.microsoft_account_email && (
                  <p className="text-xs text-text-secondary mt-1">
                    {connections.microsoft_account_email}
                  </p>
                )}
              </div>
              {connections?.microsoft_connected ? (
                <button
                  onClick={handleDisconnectMicrosoft}
                  disabled={connectionLoading}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg text-xs",
                    "border border-border text-text-secondary hover:bg-bg-elevated",
                    "disabled:opacity-60 disabled:cursor-not-allowed"
                  )}
                >
                  {connectionLoading ? <Loader2 size={14} className="animate-spin" /> : <Unplug size={14} />}
                  Ngat
                </button>
              ) : (
                <button
                  onClick={handleConnectMicrosoft}
                  disabled={connectionLoading}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg text-xs",
                    "bg-accent text-text-on-accent hover:bg-accent-hover",
                    "disabled:opacity-60 disabled:cursor-not-allowed"
                  )}
                >
                  {connectionLoading ? <Loader2 size={14} className="animate-spin" /> : <PlugZap size={14} />}
                  Ket noi
                </button>
              )}
            </div>
          </div>
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
