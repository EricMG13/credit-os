// Runs the locally installed, pinned jscpd over web/src with threshold 3. Paths come from this
// file's location, never the working directory. The Python package is scanned by tools/gates.py,
// not here. There is no npx fallback: a missing jscpd is an error.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";

const web = path.join(import.meta.dirname, "..");
const jscpd = path.join(web, "node_modules", "jscpd", "run-jscpd.js");
if (!existsSync(jscpd)) {
  console.error(`FAIL jscpd is not installed at ${jscpd}; run npm ci in web/`);
  process.exit(1);
}
const result = spawnSync(process.execPath, [jscpd, "--threshold", "3", path.join(web, "src")], {
  stdio: "inherit",
  cwd: web,
});
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
