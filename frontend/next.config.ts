import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Removed standalone mode - it breaks environment variables
  eslint: {
    ignoreDuringBuilds: true, // Skip ESLint during builds
  },
  typescript: {
    ignoreBuildErrors: true, // Skip TypeScript checks during builds
  },
};

export default nextConfig;
