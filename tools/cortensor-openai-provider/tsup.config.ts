import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
  minify: false,
  external: ['ai'],
  treeshake: true,
  target: 'es2020',
  outDir: 'dist',
  banner: {
    js: '// Cortensor AI Provider - OpenAI-compatible provider for Cortensor API',
  },
});