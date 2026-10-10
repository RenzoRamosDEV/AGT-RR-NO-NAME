import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Installable app with an offline app shell. Only the build output is precached: there is no
    // `runtimeCaching`, so API calls and anything from another origin always hit the network.
    VitePWA({
      // The user decides when to reload (see `components/UpdatePrompt`); never mid-review.
      registerType: "prompt",
      // The icons live in `public/` and are already matched by `globPatterns` below.
      includeManifestIcons: false,
      manifest: {
        name: "Duelo",
        short_name: "Duelo",
        description: "Claude Code y Codex revisan cada commit; tú decides qué review fue mejor.",
        lang: "es",
        start_url: "/",
        scope: "/",
        display: "standalone",
        theme_color: "#0d1117",
        background_color: "#0d1117",
        icons: [
          { src: "/pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "/pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/pwa-maskable-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // The app shell: build output plus the static icons copied from `public/`.
        globPatterns: ["**/*.{js,css,html,png,webp}"],
        // SPA routes resolve on the client; `/api/` is excluded in case the API is ever same-origin.
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        cleanupOutdatedCaches: true,
      },
    }),
  ],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
  },
});
