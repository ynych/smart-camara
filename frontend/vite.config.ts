import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND_TARGET = 'http://127.0.0.1:8155'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 8150,
    host: '0.0.0.0',
    proxy: {
      '/api': BACKEND_TARGET,
      '/assets': BACKEND_TARGET,
      '/content': BACKEND_TARGET,
    }
  }
})
