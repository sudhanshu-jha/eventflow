import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost',
      'sudhanshu.anlytics.dev',
    ],
    proxy: {
      '/graphql': {
        target: 'http://backend:6543',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://backend:6543',
        changeOrigin: true,
      },
    },
  },
})
