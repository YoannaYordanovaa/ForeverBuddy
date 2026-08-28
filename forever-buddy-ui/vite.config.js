import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    historyApiFallback: true,
    proxy: {
      "/chat": backendTarget,
      "/config": backendTarget,
      "/learn": backendTarget,
      "/forget": backendTarget,
      "/admin": backendTarget,
      "/debug": backendTarget,
    },
  },
})