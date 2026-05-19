/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone se activa solo en CI/Linux para producción Docker.
  // Windows local no puede crear symlinks sin admin, lo cual rompe el copy de traces.
  ...(process.env.NEXT_BUILD_STANDALONE === "true"
    ? { output: "standalone" }
    : {}),
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    typedRoutes: true,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
