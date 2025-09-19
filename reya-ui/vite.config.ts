// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

// ESM path resolution setup (keep this)
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      // If you want to use @styles/fold.css, uncomment the next line:
      // '@styles': resolve(__dirname, 'src/styles'),
    },
  },
  server: {
    proxy: {
      // API routes that should be forwarded to FastAPI on 8000
      '/settings': 'http://127.0.0.1:8000',
      '/roles': 'http://127.0.0.1:8000',
      '/tts': "http://127.0.0.1:8000",
       '/static': "http://127.0.0.1:8000",
      // add more as you wire them:
      // '/diagnostics': 'http://127.0.0.1:8000',
      // '/git': 'http://127.0.0.1:8000',
      // '/kb': 'http://127.0.0.1:8000',
    },
  },
});
