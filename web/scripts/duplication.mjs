// Runs the locally installed, pinned jscpd over web/src and, when it exists, the Python package
// at ../src. Paths come from this file's location, never the working directory. Only directories
// that exist are passed, so a missing ../src is skipped while any real duplication (or jscpd
// failure) still fails this script. There is no npx fallback: a missing jscpd is an error.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";

const web = path.join(import.meta.dirname, "..");
const jscpd = path.join(web, "node_modules", "jscpd", "run-jscpd.js");
if (!existsSync(jscpd)) {
  console.error(`FAIL jscpd is not installed at ${jscpd}; run npm ci in web/`);
  process.exit(1);
}
const dirs = [path.join(web, "src"), path.join(web, "..", "src")].filter((dir) => existsSync(dir));
const result = spawnSync(process.execPath, [jscpd, "--threshold", "3", ...dirs], {
  stdio: "inherit",
  cwd: web,
});
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
