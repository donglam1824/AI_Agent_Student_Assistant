import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Thêm nếu IP của bạn thay đổi, ví dụ: '192.168.1.x'
  allowedDevOrigins: ["192.168.1.87", "localhost"],
};

export default nextConfig;
