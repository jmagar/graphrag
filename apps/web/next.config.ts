import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* Turbopack configuration - point to the workspace root */
  turbopack: {
    root: path.join(__dirname, "../.."),
  },
  /* Allow cross-origin requests from different hostnames in dev */
  onDemandEntries: {
    maxInactiveAge: 60 * 1000,
    pagesBufferLength: 5,
  },
  /* Dev server configuration */
  devIndicators: {
    buildActivityPosition: "bottom-right",
  },
};

export default nextConfig;
