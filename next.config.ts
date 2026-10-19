import type { NextConfig } from "next";
const config: NextConfig = {
  output: "export", trailingSlash: true,
  images: { unoptimized: true },
  // A static export ships no server bundle, so tracing it only costs a pass over
  // `.next` that deletes as it goes. Nothing consumes the result.
  outputFileTracing: false,
};
export default config;
