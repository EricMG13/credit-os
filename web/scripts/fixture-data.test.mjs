import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import vm from "node:vm";

const script = path.join(import.meta.dirname, "fixture-data.mjs");
const GROUPS = ["library", "model", "run", "signal"];

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
  const fixtures = mkdtempSync(path.join(tmpdir(), "credit-os-fixtures-"));
  for (const group of GROUPS)
    writeFileSync(path.join(fixtures, `${group}.json`), files[group] ?? "{}");
  const out = path.join(mkdtempSync(path.join(tmpdir(), "credit-os-out-")), "nested");
  try {
    return body(fixtures, out);
  } finally {
    rmSync(fixtures, { recursive: true, force: true });
    rmSync(path.dirname(out), { recursive: true, force: true });
  }
}

test("the committed fixtures are accepted and data.js holds exactly what they hold", () => {
  const fixture = (group) =>
    JSON.parse(
      readFileSync(path.join(import.meta.dirname, "..", "fixtures", `${group}.json`), "utf8"),
    );
  const expected = { schema: "credit-os-data/1", issuers: fixture("library").issuers ?? [] };
  for (const group of GROUPS) {
    const committed = fixture(group);
    if ("slice" in committed) expected[group] = committed.slice;
  }
  withDirs({}, (_, out) => {
    const result = run(out);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(evaluate(path.join(out, "data.js")), expected);
  });
});

test("four empty fixtures give the schema and no issuers, and no slice", () => {
  withDirs({}, (fixtures, out) => {
    const result = run(out, fixtures);
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(evaluate(path.join(out, "data.js")), {
      schema: "credit-os-data/1",
      issuers: [],
    });
  });
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

for (const [label, group, text, mentions] of [
  ["has an unknown top-level key", "model", '{"slyce":{}}', /slyce/],
  ["carries issuers outside library.json", "run", '{"issuers":[]}', /issuers/],
  ["is an array", "signal", "[]", /JSON object/],
  ["is null", "signal", "null", /JSON object/],
  ["is a string", "signal", '"x"', /JSON object/],
  ["is broken JSON", "signal", "{", /signal\.json/],
  ["has a malformed params entry", "model", '{"params":{"/model/:a":[{"a":1}]}}', /string values/],
]) {
  test(`a fixture that ${label} fails and names its file`, () => {
    withDirs({ [group]: text }, (fixtures, out) => {
      const result = run(out, fixtures);
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, new RegExp(`${group}\\.json`));
      assert.match(result.stderr, mentions);
    });
  });
}

test("a missing fixture file fails and names it", () => {
  withDirs({}, (fixtures, out) => {
    rmSync(path.join(fixtures, "run.json"));
    mkdirSync(out, { recursive: true });
    const result = run(out, fixtures);
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /run\.json/);
  });
});

test("a __proto__ key and script-breaking text in a slice survive as written", () => {
  const slice = '{"__proto__":{"x":1},"text":"</script><!-- \u2028 \u2029"}';
  withDirs({ run: `{"slice":${slice}}` }, (fixtures, out) => {
    assert.equal(run(out, fixtures).status, 0);
    const file = path.join(out, "data.js");
    assert.ok(!readFileSync(file, "utf8").includes("</script"));
    const got = evaluate(file).run;
    assert.deepEqual(Object.keys(got), ["__proto__", "text"]);
    assert.deepEqual(got, JSON.parse(slice));
  });
});
