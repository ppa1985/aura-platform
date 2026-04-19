import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  async rewrites() {
    // Forward /api/generator/* to the FastAPI generator so the dashboard can call it directly.
    const gen = process.env.GENERATOR_URL || "http://localhost:8000";
    return {
      beforeFiles: [
        { source: "/api/generator/:path*", destination: `${gen}/:path*` },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default config;
