import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true,
      },
      '/cancel': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true,
      },
      '/shutdown': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true,
      },
      '/stream': {
        target: 'http://127.0.0.1:5050',
        changeOrigin: true,
      },
    },
  },
});
