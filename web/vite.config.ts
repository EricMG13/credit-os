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
  plugins: [react(), tailwindcss(), classicScriptTags()],
  build: {
    outDir: "dist",
    modulePreload: false,
    cssCodeSplit: false,
    rollupOptions: {
      output: { format: "iife", inlineDynamicImports: true },
    },
  },
});
