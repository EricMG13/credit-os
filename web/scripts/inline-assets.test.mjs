// Vite inlines assets under 4 kB as data: URLs, which the policy's img-src 'self' blocks.
// This builds a small fixture app with the real vite.config.ts and checks the image is a file.
import assert from "node:assert/strict";
import {
  existsSync,
  mkdtempSync,
  readdirSync,
  realpathSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { build } from "vite";

// A valid 1x1 PNG, far below the 4 kB inline limit.
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAHyO5wQAAAABJRU5ErkJggg==",
  "base64",
);

test("an image under 4 kB is emitted as a file, never as a data: URL", async (t) => {
  const root = realpathSync(mkdtempSync(path.join(tmpdir(), "credit-os-inline-")));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  writeFileSync(path.join(root, "tiny.png"), PNG);
  writeFileSync(
    path.join(root, "main.js"),
    'import tiny from "./tiny.png";\ndocument.title = tiny;\n',
  );
  writeFileSync(
    path.join(root, "index.html"),
    '<!doctype html><html><head></head><body><script type="module" src="/main.js"></script></body></html>',
  );
  const outDir = path.join(root, "out");
  await build({
    root,
    configFile: path.join(import.meta.dirname, "..", "vite.config.ts"),
    logLevel: "silent",
    build: { outDir, emptyOutDir: true },
  });
  const assets = readdirSync(path.join(outDir, "assets"));
  assert.ok(
    assets.some((name) => name.endsWith(".png")),
    `no .png file was emitted: ${assets.join(", ")}`,
  );
  const script = assets.find((name) => name.endsWith(".js"));
  assert.ok(script && existsSync(path.join(outDir, "assets", script)));
  assert.doesNotMatch(readFileSync(path.join(outDir, "assets", script), "utf8"), /data:image/);
});
