"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { connectMicrosoft } from "@/lib/api";

function getErrorMessage(err: unknown, fallback: string) {
  if (typeof err === "object" && err !== null && "response" in err) {
    const response = (err as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail) return response.data.detail;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

export default function MicrosoftCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [message, setMessage] = useState("Đang kết nối Microsoft...");

  useEffect(() => {
    const run = async () => {
      const code = params.get("code");
      const error = params.get("error_description") || params.get("error");
      if (error) {
        setMessage(error);
        return;
      }
      if (!code) {
        setMessage("Không tìm thấy authorization code từ Microsoft.");
        return;
      }

      try {
        const redirectUri = `${window.location.origin}/auth/microsoft/callback`;
        await connectMicrosoft(code, redirectUri);
        router.replace("/settings?microsoft=connected");
      } catch (err: unknown) {
        setMessage(getErrorMessage(err, "Kết nối Microsoft thất bại."));
      }
    };

    run();
  }, [params, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary p-6">
      <div className="rounded-xl border border-border bg-bg-secondary p-6 text-center max-w-sm">
        <Loader2 className="mx-auto mb-4 animate-spin text-accent" size={28} />
        <p className="text-sm text-text-primary">{message}</p>
      </div>
    </div>
  );
}
