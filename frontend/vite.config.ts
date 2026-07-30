import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // 0.0.0.0 so the devcontainer port-forward can reach it.
    host: true,
    port: 5173,
    // Talk to the FastAPI server without CORS or hardcoded hosts.
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
