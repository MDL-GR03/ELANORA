/* eslint-env node */
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';
import express from 'express';

// Detect if running in Docker
const inDocker = process.env.DOCKER === 'true';

// Custom plugin to serve external static files
function serveStaticFiles() {
  return {
    name: 'serve-static-files',
    configureServer(server) {
      const staticPath = inDocker
        ? path.resolve('/app/static')
        : path.resolve('../static');

      server.middlewares.use('/static', express.static(staticPath));
    },
  };
}

export default defineConfig(({ mode }) => {
  const envDir = '../env';
  const isDevelopment = mode === 'dev' || mode === 'dev-docker';

  const envFileMap = {
    dev: '.env.dev',
    'dev-docker': '.env.dev.docker',
    prod: '.env.prod',
    server: '.env.server',
  };

  let envFile;
  if (inDocker && mode === 'dev') {
    envFile = '.env.dev.docker';
  } else {
    envFile = envFileMap[mode] || '.env.dev';
  }

  return {
    plugins: [
      vue(),
      tailwindcss(),
      ...(isDevelopment ? [serveStaticFiles()] : []),
    ],
    envDir: envDir,
    envFile: envFile,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@api': path.resolve(__dirname, './src/api'),
        '@apiServices': path.resolve(__dirname, './src/api/services'),
        '@assets': path.resolve(__dirname, './src/assets'),
        '@components': path.resolve(__dirname, './src/components'),
        '@views': path.resolve(__dirname, './src/views'),
        '@css': path.resolve(__dirname, './src/assets/css'),
        '@images': path.resolve(__dirname, './public/images'),
        '@icons': path.resolve(__dirname, './public/images/icons'),
        '@logos': path.resolve(__dirname, './public/images/logos'),
        '@search': path.resolve(__dirname, './public/images/search'),
        '@videos': path.resolve(__dirname, './public/videos'),
        '@router': path.resolve(__dirname, './src/router'),
        '@stores': path.resolve(__dirname, './src/stores'),
        '@locales': path.resolve(__dirname, './src/locales'),
        '@utils': path.resolve(__dirname, './src/utils'),
        '@instance': path.resolve(__dirname, './instance'),
        '@plugins': path.resolve(__dirname, './src/plugins'),
      },
    },
    build: {
      modulePreload: {
        resolveDependencies: (_filename, dependencies) =>
          dependencies.filter((dependency) => !dependency.includes('/icons-')),
      },
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/@fortawesome')) return 'icons';
            return undefined;
          },
        },
      },
    },
    test: {
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
    server: {
      watch: {
        // Bind mounts need polling in Docker; native host development does not.
        usePolling: inDocker,
        interval: inDocker ? 300 : undefined,
        ignored: ['**/node_modules/**', '**/.git/**', '**/dist/**'],
      },
      host: '0.0.0.0',
      port: 8777,
      strictPort: true,
      hmr: inDocker
        ? {
            host: 'localhost',
            clientPort: 8777,
            protocol: 'ws',
          }
        : true,
      proxy: {
        '/api/v1': {
          target: inDocker ? 'http://backend:8018' : 'http://localhost:8018',
          changeOrigin: true,
          secure: false,
          configure: (proxy, options) => {
            console.log('Proxy configured with target:', options.target);
          },
        },
      },
    },
  };
});
