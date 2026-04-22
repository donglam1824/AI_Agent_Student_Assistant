import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORCA – Trợ lý AI Học tập",
  description:
    "Ứng dụng trợ lý AI học tập đa tác tử cho sinh viên. Quản lý lịch học, ghi chú, email và tìm kiếm tài liệu thông minh.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body className="min-h-screen bg-bg-primary text-text-primary font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
