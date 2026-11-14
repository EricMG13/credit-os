// Opens the built library from file:// in a headless Chromium browser and checks the page.
// Usage: node scripts/open-from-disk.mjs [distDir]
// Exit 0: every page check passed. 1: a check failed. 77: no browser found and CI is unset.
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { assetProblems, fontProblems, referencedAssets } from "./assets.mjs";
import { classProblems, focusOutlineProblems } from "./classes.mjs";
import { checkRoutes } from "./route-visits.mjs";

const distDir = path.resolve(process.argv[2] ?? "dist");
// A hung browser must fail the run, not hold the CI job until the runner limit.
const browserTimeoutMs = Number(process.env["CREDIT_OS_BROWSER_TIMEOUT_MS"] ?? 60000);

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

function dumpPage(browser, folder, hash = "") {
  const profile = mkdtempSync(path.join(tmpdir(), "credit-os-profile-"));
  const url = pathToFileURL(path.join(folder, "index.html")).href + hash;
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
  const run = spawnSync(browser, args, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    timeout: browserTimeoutMs,
    killSignal: "SIGKILL",
  });
  // Windows can hold profile files briefly after the browser exits, so removal retries.
  rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  if (run.error?.code === "ETIMEDOUT") {
    throw new Error(`the browser did not finish within ${browserTimeoutMs} ms and was killed`);
  }
  if (run.error) throw run.error;
  return { dom: run.stdout, log: run.stderr };
}

// Chrome logs page console output and security violations to stderr. A violation is reported
// as "... violates the following Content Security Policy directive ..."; an uncaught page
// error is logged as "Uncaught ...". Other stderr lines (GPU, updater, dbus) are ignored.
// A stylesheet or script that Chrome refuses from file:// (for example a leftover crossorigin
// attribute) is logged as "Access to CSS stylesheet at ... has been blocked by CORS policy".
function problems(log) {
  return ["Content Security Policy", "Uncaught", "blocked by CORS policy"].filter((needle) =>
    log.includes(needle),
  );
}

function checkAssets(folder) {
  const problems = assetProblems(folder);
  const ok = problems.length === 0;
  console.log(
    `${ok ? "PASS" : "FAIL"} referenced assets are sound: ${referencedAssets(folder).assets.length} found`,
  );
  for (const problem of problems) console.log(`  ${problem}`);
  return ok;
}

function checkStyleUrls(folder) {
  const problems = fontProblems(folder);
  const ok = problems.length === 0;
  console.log(`${ok ? "PASS" : "FAIL"} every url() in the stylesheet is relative and exists`);
  for (const problem of problems) console.log(`  ${problem}`);
  return ok;
}

// Strings in the source that look like colour, shadow, radius or size classes but are not.
// Each entry carries its reason. Empty today.
const NOT_CLASSES = [];

// A class with no rule in the built stylesheet draws nothing, because the default palette is off.
function checkClasses(folder) {
  const css = referencedAssets(folder)
    .assets.filter(({ kind, ref }) => kind === "stylesheet" && ref !== undefined)
    .map(({ ref }) => readFileSync(path.join(folder, ...ref.split("/")), "utf8"))
    .join("\n");
  const srcDir = path.resolve(import.meta.dirname, "..", "src");
  const problems = [...classProblems(srcDir, css, NOT_CLASSES), ...focusOutlineProblems(srcDir)];
  const ok = problems.length === 0;
  console.log(`${ok ? "PASS" : "FAIL"} every colour, shadow, radius and size class has a rule`);
  for (const problem of problems) console.log(`  ${problem}`);
  return ok;
}

function check(label, browser, folder, expected, hash = "", forbidden = []) {
  const { dom, log } = dumpPage(browser, folder, hash);
  const found = problems(log);
  const present = forbidden.filter((text) => dom.includes(text));
  const ok = dom.includes(expected) && found.length === 0 && present.length === 0;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}: expects "${expected}"`);
  if (!ok) {
    if (!dom.includes(expected)) console.log(`  the page text did not contain it`);
    for (const needle of found) console.log(`  stderr contains "${needle}"`);
    for (const text of present) console.log(`  the live DOM contains "${text}"`);
    console.log(`  stderr:\n${log}\n  dom:\n${dom}`);
  }
  return ok;
}

// Positive control for the violation detector. A copy of the built page gets an inline <style>
// element, which the policy forbids, so the browser must log a violation. If it does not, the
// browser's log never reaches this script and a green run on the real page proves nothing.
function canary(browser, folder, scratch) {
  const copy = path.join(scratch, "canary");
  cpSync(folder, copy, { recursive: true });
  const page = path.join(copy, "index.html");
  const html = readFileSync(page, "utf8");
  const marked = html.replace("</head>", "<style>body{color:red}</style></head>");
  if (marked === html) throw new Error("the canary could not be added: no </head> in index.html");
  writeFileSync(page, marked);
  const { log } = dumpPage(browser, copy);
  const ok = problems(log).includes("Content Security Policy");
  console.log(`${ok ? "PASS" : "FAIL"} violation canary: an inline <style> must be reported`);
  if (!ok) {
    console.log(
      "  the browser did not report the deliberate violation, so its logging cannot be trusted",
    );
    console.log(`  stderr:\n${log}`);
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
  const results = [checkAssets(folder), checkStyleUrls(folder), checkClasses(folder)];
  results.push(check("data.js present", browser, folder, "No runs yet"));
  // The dump is the live DOM: a style element injected by a library would appear in it.
  results.push(
    check("component kit, no injected style", browser, folder, "Component kit", "#/kit", [
      "<style",
    ]),
  );
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
  const populated = original.replace(
    /issuers:\s*\[\s*\]/,
    'issuers: [{ id: "tdg", name: "TransDigm" }]',
  );
  if (populated === original) throw new Error("data.js has no empty issuers list to fill");
  writeFileSync(dataFile, populated);
  results.push(check("data.js with one issuer", browser, folder, "TransDigm"));
  writeFileSync(dataFile, original);
  results.push(checkRoutes({ browser, folder, work, dumpPage, problems }));
  results.push(canary(browser, folder, work));
  allOk = results.every(Boolean);
} finally {
  rmSync(work, { recursive: true, force: true });
}
process.exit(allOk ? 0 : 1);
