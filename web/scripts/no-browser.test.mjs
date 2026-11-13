// The "no browser found" path of open-from-disk.mjs and of the gates wrapper, run for real.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";

const scripts = import.meta.dirname;
const emptyPath = mkdtempSync(path.join(tmpdir(), "credit-os-nopath-"));

function run(script, ci) {
  const env = { ...process.env, CHROME_PATH: path.join(emptyPath, "no-browser"), PATH: emptyPath };
  delete env["CI"];
  if (ci) env["CI"] = "true";
  const out = spawnSync(process.execPath, [path.join(scripts, script)], { env, encoding: "utf8" });
  return { status: out.status, text: `${out.stdout}${out.stderr}` };
}

test.after(() => {
  rmSync(emptyPath, { recursive: true, force: true });
});

test("open-from-disk: no browser and CI unset exits 77 with the reason", () => {
  const out = run("open-from-disk.mjs", false);
  assert.equal(out.status, 77);
  assert.match(out.text, /SKIP no supported browser found/);
});

test("open-from-disk: no browser and CI=true exits 1 with the reason", () => {
  const out = run("open-from-disk.mjs", true);
  assert.equal(out.status, 1);
  assert.match(out.text, /FAIL no supported browser found/);
});

test("file-check: 77 is a skip, one clear line, exit 0", () => {
  const out = run("file-check.mjs", false);
  assert.equal(out.status, 0);
  assert.match(out.text, /SKIPPED browser check/);
});

test("file-check: CI=true with no browser is a failure, never a skip", () => {
  const out = run("file-check.mjs", true);
  assert.equal(out.status, 1);
  assert.doesNotMatch(out.text, /SKIPPED/);
});

test("file-check: a browser check that really fails exits 1 and is never reported as a skip", (t) => {
  if (process.platform === "win32") {
    t.skip("the stub browser is a POSIX script");
    return;
  }
  const stubDir = mkdtempSync(path.join(tmpdir(), "credit-os-stub-"));
  t.after(() => rmSync(stubDir, { recursive: true, force: true }));
  const stub = path.join(stubDir, "stub-browser");
  // A browser that opens nothing: it prints no page, so every page check fails.
  writeFileSync(stub, `#!${process.execPath}\nprocess.exit(0);\n`);
  chmodSync(stub, 0o755);
  const env = { ...process.env, CHROME_PATH: stub };
  delete env["CI"];
  const out = spawnSync(process.execPath, [path.join(scripts, "file-check.mjs")], {
    env,
    encoding: "utf8",
  });
  const text = `${out.stdout}${out.stderr}`;
  assert.equal(out.status, 1);
  assert.match(text, /FAIL data\.js present/);
  assert.doesNotMatch(text, /SKIPPED/);
});
