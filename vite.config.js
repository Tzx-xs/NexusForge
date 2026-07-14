import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src')
        }
    },
    optimizeDeps: {
        include: [
            'vue',
            'vue-router',
            'pinia',
            '@vueuse/core'
        ]
    },
    build: {
        outDir: 'dist',
        chunkSizeWarningLimit: 1500,
        rollupOptions: {
            output: {
                manualChunks: {
                    'vue-vendor': ['vue', 'vue-router', 'pinia']
                }
            }
        }
    },
    server: {
        port: 3000,
        open: true,
        host: true
    },
    preview: {
        port: 4173
    }
});
