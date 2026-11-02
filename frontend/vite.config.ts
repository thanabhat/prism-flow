import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendTarget = process.env.BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    target: "esnext",
  },
  optimizeDeps: {
    exclude: [
      "@perspective-dev/client",
      "@perspective-dev/viewer",
      "@perspective-dev/viewer-datagrid",
      "@perspective-dev/viewer-charts",
    ],
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/ws": {
        target: backendTarget.replace(/^http/, "ws"),
        ws: true,
      },
    },
  },
});
