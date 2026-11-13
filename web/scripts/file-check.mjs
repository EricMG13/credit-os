// The browser check as the gates run it: build, then open-from-disk.mjs.
// Exit 77 from open-from-disk.mjs (no browser, CI unset) is a skip: one line, exit 0.
// Every other non-zero status is a failure and is returned as it came.
import { spawnSync } from "node:child_process";
import path from "node:path";

const here = import.meta.dirname;
const run = (script, args) =>
  spawnSync(process.execPath, [script, ...args], { stdio: "inherit", cwd: path.join(here, "..") });

const build = run(path.join("node_modules", "vite", "bin", "vite.js"), ["build"]);
if (build.status !== 0) process.exit(build.status ?? 1);

const check = run(path.join("scripts", "open-from-disk.mjs"), []);
if (check.status === 77 && !process.env["CI"]) {
  console.log("SKIPPED browser check on file:// (no browser found); set CI=true to require it");
  process.exit(0);
}
process.exit(check.status ?? 1);
