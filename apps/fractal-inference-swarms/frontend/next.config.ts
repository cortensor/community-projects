/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // allowedDevOrigins is usually not needed for localhost, but keep if using custom domains
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        // 🔴 FIX: Change 'localhost' to '127.0.0.1'
        destination: 'http://127.0.0.1:3001/api/:path*', 
      },
    ];
  },
};

module.exports = nextConfig;