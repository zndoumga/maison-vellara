import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Allow builds to succeed even with TS errors in components using dynamic data
  typescript: { ignoreBuildErrors: false },
}

export default nextConfig
