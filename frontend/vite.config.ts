import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { backendProxyUrl } from "./src/devServerConfig";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/testSetup.ts",
  },
  server: {
    port: 5173,
    proxy: {
      "/api": backendProxyUrl(),
    },
  },
});

