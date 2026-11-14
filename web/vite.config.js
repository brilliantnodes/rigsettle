import { defineConfig } from "vite";

// The site is static. It is built into ../docs so GitHub Pages can serve it.
// genlayer-js (with viem) is about 570 kB minified and 130 kB gzipped. It is
// split into its own long-cached chunk, so a site change does not make
// returning visitors download it again; the page text renders before it loads.
export default defineConfig({
  base: "./",
  build: {
    outDir: "../docs",
    emptyOutDir: true,
    target: "es2022",
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) return "genlayer";
        },
      },
    },
  },
});
