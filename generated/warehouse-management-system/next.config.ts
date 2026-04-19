import type { NextConfig } from "next";

const config: NextConfig = {
  basePath: process.env.AURA_BASE_PATH || "/generated/warehouse-management-system",
  output: "standalone",
  experimental: {
    typedRoutes: false,
  },
};

export default config;
