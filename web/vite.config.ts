import path from "node:path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// A module script, and a crossorigin stylesheet, are blocked from file:// ("origin null"),
// which is how the library is opened. The build emits one classic IIFE script and this plugin
// rewrites the tags Vite injects: no type="module", no crossorigin, deferred.
function classicScriptTags(): Plugin {
  return {
    name: "credit-os-classic-script-tags",
    transformIndexHtml: {
      order: "post",
      handler(html) {
        return html
          .replace(
            /<script type="module" crossorigin src="([^"]+)"><\/script>/g,
            '<script defer src="$1"></script>',
          )
          .replace(
            /<link rel="stylesheet" crossorigin href="([^"]+)">/g,
            '<link rel="stylesheet" href="$1">',
          );
      },
    },
  };
}

export default defineConfig({
  base: "./",
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  plugins: [react(), tailwindcss(), classicScriptTags()],
  build: {
    outDir: "dist",
    // Vite inlines assets under 4 kB as data: URLs, which the policy's img-src 'self' blocks.
    assetsInlineLimit: 0,
    modulePreload: false,
    cssCodeSplit: false,
    rollupOptions: {
      output: { format: "iife", inlineDynamicImports: true },
    },
  },
});
