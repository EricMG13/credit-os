// The browser creates DevToolsActivePort before it has finished writing it, and on Windows holds
// it open: readDebugPort must wait for a complete first line and retry a held file.
// Each case runs on a real temporary folder; the injected wait performs the next step of the
// scenario, so no case sleeps on a real clock.
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, beforeEach, test } from "node:test";
import { readDebugPort } from "./kit-chrome.mjs";

let profile;
let portFile;
beforeEach(() => {
  profile = mkdtempSync(path.join(tmpdir(), "kit-chrome-test-"));
  portFile = path.join(profile, "DevToolsActivePort");
});
afterEach(() => rmSync(profile, { recursive: true, force: true }));

// A wait that runs the scenario's steps in order, one per call, and counts its calls.
function script(...steps) {
  const wait = async () => {
    wait.calls++;
    steps[wait.calls - 1]?.();
  };
  wait.calls = 0;
  return wait;
}
const put = (text) => () => writeFileSync(portFile, text);
const held = (code) => Object.assign(new Error(`read failed: ${code}`), { code });

test("an empty file is retried until the first line is complete", async () => {
  writeFileSync(portFile, "");
  const wait = script(put("9222\n/devtools/browser/abc"));
  assert.equal(await readDebugPort(profile, { wait, tries: 10 }), "9222");
});

test("a first line counts only once a newline follows it", async () => {
  writeFileSync(portFile, "");
  const wait = script(put("92"), put("9222\n/devtools/browser/abc"));
  assert.equal(await readDebugPort(profile, { wait, tries: 10 }), "9222");
  assert.equal(wait.calls, 2);
});

test("a missing file is waited for", async () => {
  const wait = script(put("9222\n/x"));
  assert.equal(await readDebugPort(profile, { wait, tries: 10 }), "9222");
});

test("EBUSY, EPERM and EACCES reads are retried", async () => {
  writeFileSync(portFile, "9222\n/x");
  const codes = ["EBUSY", "EBUSY", "EPERM", "EACCES"];
  const read = () => {
    const code = codes.shift();
    if (code) throw held(code);
    return "9222\n/x";
  };
  assert.equal(await readDebugPort(profile, { wait: script(), tries: 10, read }), "9222");
  assert.deepEqual(codes, []);
});

test("any other read error is thrown at once, unchanged", async () => {
  writeFileSync(portFile, "9222\n/x");
  const error = held("ENOSPC");
  const wait = script();
  await assert.rejects(
    readDebugPort(profile, {
      wait,
      tries: 10,
      read: () => {
        throw error;
      },
    }),
    (thrown) => thrown === error,
  );
  assert.equal(wait.calls, 0);
});

test("when the budget runs out the error names what was last seen", async () => {
  const wait = script();
  await assert.rejects(
    readDebugPort(profile, { wait, tries: 5 }),
    /the browser did not open its debugging port \(last seen: file missing\)/,
  );
  assert.equal(wait.calls, 5);
  writeFileSync(portFile, "");
  await assert.rejects(
    readDebugPort(profile, { wait: script(), tries: 3 }),
    /debugging port \(last seen: empty first line\)/,
  );
  await assert.rejects(
    readDebugPort(profile, {
      wait: script(),
      tries: 3,
      read: () => {
        throw held("EBUSY");
      },
    }),
    /debugging port \(last seen: EBUSY\)/,
  );
});

test("a first line that is not a port from 1 to 65535 is not ready", async () => {
  for (const line of ["0", "70000", "12ab", "65536"]) {
    writeFileSync(portFile, `${line}\n/x`);
    await assert.rejects(
      readDebugPort(profile, { wait: script(), tries: 3 }),
      new RegExp(`debugging port \\(last seen: first line "${line}"\\)`),
    );
  }
  writeFileSync(portFile, "65535\n/x");
  assert.equal(await readDebugPort(profile, { wait: script(), tries: 3 }), "65535");
});
