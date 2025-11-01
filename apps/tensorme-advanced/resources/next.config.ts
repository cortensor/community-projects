import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL: process.env.NEXT_PUBLIC_ARBITRUM_SEPOLIA_RPC_URL,
    NEXT_PUBLIC_SESSION_V2_ADDRESS: process.env.NEXT_PUBLIC_SESSION_V2_ADDRESS,
    NEXT_PUBLIC_SESSION_QUEUE_V2_ADDRESS: process.env.NEXT_PUBLIC_SESSION_QUEUE_V2_ADDRESS,
  }
};

export default nextConfig;
