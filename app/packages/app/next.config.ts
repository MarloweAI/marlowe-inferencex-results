import type { NextConfig } from 'next';

// A static export for GitHub Pages: the inference chart page only, reading JSON snapshots from /data/api/.
const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || undefined,
  distDir: process.env.NEXT_DIST_DIR || '.next',
  transpilePackages: ['@semianalysisai/inferencex-constants'],
  typescript: { ignoreBuildErrors: true },
  experimental: {
    optimizePackageImports: ['lucide-react', 'd3', '@tanstack/react-query'],
  },
  images: { unoptimized: true },
};

export default nextConfig;
