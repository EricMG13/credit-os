import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import vm from "node:vm";

const script = path.join(import.meta.dirname, "fixture-data.mjs");
const GROUPS = ["library", "model", "run", "signal"];

function fixturesDir(files) {
  const dir = mkdtempSync(path.join(tmpdir(), "credit-os-fixtures-"));
  for (const group of GROUPS) writeFileSync(path.join(dir, `${group}.json`), files[group] ?? "{}");
  return dir;
}

function run(outDir, fixtures) {
  return spawnSync(process.execPath, [script, outDir, ...(fixtures ? [fixtures] : [])], {
    encoding: "utf8",
  });
}

function evaluate(file) {
  const context = { window: {} };
  vm.runInNewContext(readFileSync(file, "utf8"), context);
  // Objects made inside the vm context have another Object prototype: copy them out as plain data.
  return JSON.parse(JSON.stringify(context.window.CREDIT_OS_DATA));
}

function withDirs(files, body) {
  const fixtures = fixturesDir(files);
  const out = path.join(mkdtempSync(path.join(tmpdir(), "credit-os-out-")), "nested");
  try {
    return body(fixtures, out);
  } finally {
    rmSync(fixtures, { recursive: true, force: true });
    rmSync(path.dirname(out), { recursive: true, force: true });
  }
}

test("the committed fixtures produce a data.js with the schema, no issuers and no slices", () => {
  const out = mkdtempSync(path.join(tmpdir(), "credit-os-out-"));
  try {
    const result = run(out);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(evaluate(path.join(out, "data.js")), {
      schema: "credit-os-data/1",
      issuers: [],
    });
  } finally {
    rmSync(out, { recursive: true, force: true });
  }
});

test("data.js carries exactly the slices the fixtures have, and the library's issuers", () => {
  const files = {
    library: JSON.stringify({ slice: { n: 1 }, issuers: [{ id: "x", name: "X" }] }),
    run: JSON.stringify({ slice: [] }),
    signal: JSON.stringify({ params: { "/signal/:id": [{ id: "a" }] } }),
  };
  withDirs(files, (fixtures, out) => {
    const result = run(out, fixtures);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(evaluate(path.join(out, "data.js")), {
      schema: "credit-os-data/1",
      issuers: [{ id: "x", name: "X" }],
      library: { n: 1 },
      run: [],
    });
  });
});

test("a fixture with an unknown top-level key fails and names its file", () => {
  withDirs({ model: JSON.stringify({ slyce: {} }) }, (fixtures, out) => {
    const result = run(out, fixtures);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /model\.json/);
    assert.match(result.stderr, /slyce/);
  });
});

test("issuers belong to library.json only", () => {
  withDirs({ run: JSON.stringify({ issuers: [] }) }, (fixtures, out) => {
    const result = run(out, fixtures);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /run\.json/);
  });
});

for (const [label, text] of [
  ["an array", "[]"],
  ["null", "null"],
  ["a string", '"x"'],
  ["broken JSON", "{"],
]) {
  test(`a fixture that is ${label} fails and names its file`, () => {
    withDirs({ signal: text }, (fixtures, out) => {
      const result = run(out, fixtures);
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, /signal\.json/);
    });
  });
}

test("a malformed params entry fails and names its file", () => {
  withDirs({ model: JSON.stringify({ params: { "/model/:a": [{ a: 1 }] } }) }, (fixtures, out) => {
    const result = run(out, fixtures);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /model\.json/);
  });
});

test("a missing fixture file fails and names it", () => {
  withDirs({}, (fixtures, out) => {
    rmSync(path.join(fixtures, "run.json"));
    mkdirSync(out, { recursive: true });
    const result = run(out, fixtures);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /run\.json/);
  });
});
