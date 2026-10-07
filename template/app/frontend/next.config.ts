import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The UI ships TypeScript source; let Next transpile it.
  transpilePackages: ["@docextract/ui"],
};

export default nextConfig;
