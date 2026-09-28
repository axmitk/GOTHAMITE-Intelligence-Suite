import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: { assetsDir: 'static' },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8042',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8042',
        changeOrigin: true,
      },
    },
  },
});
