// Opens the built library from file:// in a headless Chromium browser and checks the page.
// Usage: node scripts/open-from-disk.mjs [distDir]
// Exit 0: every page check passed. 1: a check failed. 77: no browser found and CI is unset.
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const distDir = path.resolve(process.argv[2] ?? "dist");

function windowsCandidates() {
  const roots = [process.env["ProgramFiles"], process.env["ProgramFiles(x86)"]].filter(Boolean);
  return roots.flatMap((root) => [
    path.join(root, "Microsoft", "Edge", "Application", "msedge.exe"),
    path.join(root, "Google", "Chrome", "Application", "chrome.exe"),
  ]);
}

function onPath(name) {
  const finder = process.platform === "win32" ? "where" : "which";
  const found = spawnSync(finder, [name], { encoding: "utf8" });
  if (found.status !== 0) return undefined;
  return found.stdout.split(/\r?\n/).find((line) => line.trim() !== "");
}

function findBrowser() {
  const fromEnv = process.env["CHROME_PATH"];
  if (fromEnv) return existsSync(fromEnv) ? fromEnv : undefined;
  const fixed = [
    ...windowsCandidates(),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  ].find((candidate) => existsSync(candidate));
  if (fixed) return fixed;
  for (const name of ["google-chrome", "chromium", "microsoft-edge"]) {
    const found = onPath(name);
    if (found) return found;
  }
  return undefined;
}

function dumpPage(browser, folder) {
  const profile = mkdtempSync(path.join(tmpdir(), "credit-os-profile-"));
  const url = pathToFileURL(path.join(folder, "index.html")).href;
  const args = [
    "--headless=new",
    "--dump-dom",
    "--virtual-time-budget=5000",
    "--enable-logging=stderr",
    `--user-data-dir=${profile}`,
    "--disable-gpu",
    ...(process.env["CI"] ? ["--no-sandbox"] : []),
    url,
  ];
  const run = spawnSync(browser, args, { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  rmSync(profile, { recursive: true, force: true });
  if (run.error) throw run.error;
  return { dom: run.stdout, log: run.stderr };
}

// Chrome logs page console output and security violations to stderr. A violation is reported
// as "... violates the following Content Security Policy directive ..."; an uncaught page
// error is logged as "Uncaught ...". Other stderr lines (GPU, updater, dbus) are ignored.
function problems(log) {
  return ["Content Security Policy", "Uncaught"].filter((needle) => log.includes(needle));
}

function check(label, browser, folder, expected) {
  const { dom, log } = dumpPage(browser, folder);
  const found = problems(log);
  const ok = dom.includes(expected) && found.length === 0;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}: expects "${expected}"`);
  if (!ok) {
    if (!dom.includes(expected)) console.log(`  the page text did not contain it`);
    for (const needle of found) console.log(`  stderr contains "${needle}"`);
    console.log(`  stderr:\n${log}\n  dom:\n${dom}`);
  }
  return ok;
}

const browser = findBrowser();
if (!browser) {
  const reason = "no supported browser found (set CHROME_PATH, or install Chrome or Edge)";
  if (process.env["CI"]) {
    console.error(`FAIL ${reason}`);
    process.exit(1);
  }
  console.log(`SKIP ${reason}`);
  process.exit(77);
}
console.log(`browser: ${browser}`);

const work = mkdtempSync(path.join(tmpdir(), "credit-os-file-"));
const folder = path.join(work, "credit os é");
let allOk = false;
try {
  cpSync(distDir, folder, { recursive: true });
  const dataFile = path.join(folder, "data.js");
  const original = readFileSync(dataFile, "utf8");
  const results = [];
  results.push(check("data.js present", browser, folder, "No runs yet"));
  rmSync(dataFile);
  results.push(check("data.js deleted", browser, folder, "Library data is missing"));
  writeFileSync(dataFile, original.replace("credit-os-data/1", "credit-os-data/2"));
  results.push(
    check(
      "schema credit-os-data/2",
      browser,
      folder,
      "This library was written by a newer version",
    ),
  );
  allOk = results.every(Boolean);
} finally {
  rmSync(work, { recursive: true, force: true });
}
process.exit(allOk ? 0 : 1);
