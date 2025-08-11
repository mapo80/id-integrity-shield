import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: env.VITE_PROXY_API === '1' ? {
        '/v1': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        }
      } : undefined
    }
  }
})
