// Runs jscpd over web/src and, when it exists, the Python package at ../src.
// Only directories that exist are passed, so a missing ../src is skipped while any
// real duplication (or jscpd failure) still fails this script.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";

const dirs = ["src", "../src"].filter((dir) => existsSync(dir));
const npx = process.platform === "win32" ? "npx.cmd" : "npx";
const result = spawnSync(npx, ["jscpd", "--threshold", "3", ...dirs], {
  stdio: "inherit",
  shell: process.platform === "win32",
});
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
