import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: ['cheerio'],
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals = [...config.externals, 'cheerio'];
    }
    return config;
  }
};

export default nextConfig;
