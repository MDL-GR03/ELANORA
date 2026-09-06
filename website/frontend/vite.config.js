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
        '@': '/src',
        '@api': '/src/api',
        '@apiServices': '/src/api/services',
        '@assets': '/src/assets',
        '@components': '/src/components',
        '@views': '/src/views',
        '@css': '/src/assets/css',
        '@images': '/images',
        '@icons': '/images/icons',
        '@logos': '/images/logos',
        '@search': '/images/search',
        '@videos': '/videos',
        '@router': '/src/router',
        '@stores': '/src/stores',
        '@locales': '/src/locales',
        '@utils': '/src/utils',
        '@instance': '/instance',
        '@plugins': '/src/plugins',
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
