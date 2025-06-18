/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: [],
  },
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/**',
      },
    ],
  },
  env: {
    DEEPSEARCH_API_URL: process.env.DEEPSEARCH_API_URL || 'http://localhost:8000',
  },
};

export default nextConfig;

