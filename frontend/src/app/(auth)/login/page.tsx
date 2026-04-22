/**
 * Login page – Google OAuth sign-in with feature showcase.
 */

"use client";

import { Calendar, StickyNote, Mail, BookOpen } from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";

const FEATURES = [
  { icon: Calendar, label: "Quản lý lịch học", desc: "Tạo, xem lịch qua Google Calendar" },
  { icon: StickyNote, label: "Ghi chú thông minh", desc: "Ghi chú bằng lệnh ngôn ngữ tự nhiên" },
  { icon: Mail, label: "Email học thuật", desc: "Đọc, tóm tắt, soạn email" },
  { icon: BookOpen, label: "Tìm kiếm tài liệu", desc: "Hỏi đáp từ PDF, DOCX, TXT" },
];

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAppStore();

  const handleDemoLogin = () => {
    // Demo login – skip Google OAuth for development
    const demoUser = {
      id: "demo-user",
      email: "sinhvien@demo.edu.vn",
      name: "Sinh viên Demo",
      picture: null,
    };
    setAuth(demoUser, "demo-token");
    router.push("/chat");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 gradient-bg-light dark:gradient-bg-dark relative">
      {/* Theme toggle */}
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md animate-scale-in">
        {/* Logo & branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent/10 mb-4">
            <span className="text-3xl">🐋</span>
          </div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">
            ORCA
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Trợ lý AI học tập cá nhân của bạn
          </p>
        </div>

        {/* Login card */}
        <div
          className={cn(
            "rounded-2xl p-6",
            "bg-bg-primary/80 dark:bg-bg-secondary/80",
            "backdrop-blur-xl border border-border",
            "shadow-lg"
          )}
        >
          {/* Google Sign-in button */}
          <button
            id="google-login-btn"
            onClick={handleDemoLogin}
            className={cn(
              "w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl",
              "bg-accent text-text-on-accent font-medium text-sm",
              "hover:bg-accent-hover transition-colors duration-200",
              "shadow-sm"
            )}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" className="flex-shrink-0">
              <path
                d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
                fill="#4285F4"
              />
              <path
                d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
                fill="#34A853"
              />
              <path
                d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.997 8.997 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
                fill="#FBBC05"
              />
              <path
                d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
                fill="#EA4335"
              />
            </svg>
            Đăng nhập bằng Google
          </button>

          <p className="text-[11px] text-text-secondary text-center mt-3">
            Cấp quyền truy cập Google Calendar & Gmail
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-2 gap-3 mt-6">
          {FEATURES.map(({ icon: Icon, label, desc }) => (
            <div
              key={label}
              className={cn(
                "p-3.5 rounded-xl",
                "bg-bg-primary/60 dark:bg-bg-secondary/60",
                "backdrop-blur-sm border border-border/50",
                "animate-slide-up"
              )}
            >
              <Icon size={20} className="text-accent mb-2" />
              <p className="text-xs font-medium text-text-primary">{label}</p>
              <p className="text-[10px] text-text-secondary mt-0.5 leading-relaxed">
                {desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
