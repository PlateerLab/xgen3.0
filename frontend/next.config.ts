import type { NextConfig } from 'next';

const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

const nextConfig: NextConfig = {
  sassOptions: {
    silenceDeprecations: ['legacy-js-api'],
  },
  async rewrites() {
    return [
      {
        source: '/api/workflow/:path*',
        destination: `${backendUrl}/api/workflow/:path*`,
      },
      {
        source: '/api/agent/:path*',
        destination: `${backendUrl}/api/agent/:path*`,
      },
      {
        source: '/api/tools/:path*',
        destination: `${backendUrl}/api/tools/:path*`,
      },
      {
        source: '/api/mcp/:path*',
        destination: `${backendUrl}/api/mcp/:path*`,
      },
      {
        source: '/health',
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
