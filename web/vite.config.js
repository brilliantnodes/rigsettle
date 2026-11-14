import { defineConfig } from "vite";

// The site is static. It is built into ../docs so GitHub Pages can serve it.
export default defineConfig({
  base: "./",
  build: { outDir: "../docs", emptyOutDir: true, target: "es2022" },
});
