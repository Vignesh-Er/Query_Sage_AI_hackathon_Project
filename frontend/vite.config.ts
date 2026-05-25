import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/@monaco-editor") || id.includes("node_modules/monaco-editor")) {
            return "monaco";
          }
          if (id.includes("node_modules/@xyflow") || id.includes("node_modules/reactflow")) {
            return "xyflow";
          }
          if (id.includes("node_modules/echarts")) {
            return "echarts";
          }
          if (id.includes("node_modules/framer-motion")) {
            return "framer-motion";
          }
          if (id.includes("node_modules/d3")) {
            return "d3";
          }
          if (id.includes("node_modules")) {
            return "vendor";
          }
          return undefined;
        }
      }
    }
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8421",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  worker: {
    format: "es",
  }
});
