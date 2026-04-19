import type { NextConfig } from "next";

// /api/generator/* is proxied to the FastAPI generator via a Route Handler at
// src/app/api/generator/[...path]/route.ts so that GENERATOR_URL is read at
// request time. A next.config rewrite would bake the value into
// routes-manifest.json at build time and ignore the runtime container env.

const config: NextConfig = {
  output: "standalone",
};

export default config;
