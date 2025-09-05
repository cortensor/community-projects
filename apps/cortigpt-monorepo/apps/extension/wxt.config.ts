import { defineConfig } from 'wxt';
import path from 'path';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  alias: {
    '@': path.resolve(__dirname, './'),
  },
  vite: () => ({
    css: {
      postcss: {
        plugins: [
          require('tailwindcss'),
          require('autoprefixer'),
        ],
      },
    },
  }),
  webExt: {
    disabled:true
  },
  manifest: {
    permissions: ['sidePanel', 'storage', 'activeTab', 'tabs'],
    host_permissions: ['<all_urls>'],
    // content_security_policy: {
    //   extension_pages: "script-src 'self'; object-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:;"
    // },
    side_panel: {
      default_path: 'sidepanel.html'
    },
    action: {
      default_title: 'cortigpt - decentralized perplexity'
    },
    icons: {
      16: '/cortigpt-4.png',
      24: '/cortigpt-4.png',
      48: '/cortigpt-4.png',
      96: '/cortigpt-4.png',
      128: '/cortigpt-4.png',
    },
  },
});
