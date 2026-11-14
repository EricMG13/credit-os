// The class coverage check, run on small source folders and stylesheets.
import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import {
  builtClasses,
  classProblems,
  focusOutlineProblems,
  hiddenFocusOutline,
  utilityTokens,
} from "./classes.mjs";

const roots = [];

function src(files) {
  const root = mkdtempSync(path.join(tmpdir(), "credit-os-classes-"));
  roots.push(root);
  for (const [name, body] of Object.entries(files)) writeFileSync(path.join(root, name), body);
  return root;
}

test.after(() => {
  for (const root of roots) rmSync(root, { recursive: true, force: true });
});

test("a class with a rule in the stylesheet passes", () => {
  const root = src({ "a.tsx": 'export const c = "bg-primary text-secondary";' });
  assert.deepEqual(classProblems(root, ".bg-primary{a:b}.text-secondary{a:b}", []), []);
});

test("a class with no rule is reported with its file", () => {
  const root = src({ "a.tsx": 'export const c = "bg-primary bg-does-not-exist";' });
  assert.deepEqual(classProblems(root, ".bg-primary{a:b}", []), [
    "a.tsx: bg-does-not-exist has no rule in the built stylesheet",
  ]);
});

test("a variant-prefixed class is checked by its escaped selector", () => {
  const root = src({
    "a.ts": 'export const c = "hover:bg-ok focus-visible:ring-missing";',
  });
  const css = ".hover\\:bg-ok:hover{a:b}";
  assert.deepEqual(classProblems(root, css, []), [
    "a.ts: focus-visible:ring-missing has no rule in the built stylesheet",
  ]);
});

test("escaped dots, slashes, percents and brackets in selectors are read back", () => {
  const css =
    ".px-4\\.5{a:b}.before\\:border-white\\/12:before{a:b}.rounded-\\[7px\\]{a:b}.from-0\\%{a:b}";
  const found = builtClasses(css);
  for (const name of ["px-4.5", "before:border-white/12", "rounded-[7px]", "from-0%"]) {
    assert.ok(found.has(name), name);
  }
});

test("hex escapes in selectors are read back", () => {
  assert.ok(builtClasses(".\\31 0{a:b}").has("10"));
});

test("a colon inside a bracketed variant does not hide the utility", () => {
  assert.deepEqual(utilityTokens('"[&>*:not([data-x])]:bg-nope hover:flex"'), [
    "[&>*:not([data-x])]:bg-nope",
  ]);
});

test("strings that are not colour, shadow, radius or size classes are ignored", () => {
  assert.deepEqual(
    utilityTokens('const a = "flex p-4 ./styles/theme.css react-aria-components"'),
    [],
  );
});

test("every utility family is checked", () => {
  const families =
    "bg-a text-a border-a ring-a outline-a fill-a stroke-a divide-a shadow-a rounded-a from-a to-a via-a";
  assert.equal(utilityTokens(`"${families}"`).length, 13);
});

test("test files are not scanned", () => {
  const root = src({ "a.test.tsx": 'export const c = "bg-does-not-exist";', "b.ts": "export {};" });
  assert.deepEqual(classProblems(root, "", []), []);
});

test("an allowlisted token is skipped", () => {
  const root = src({ "a.ts": 'export const c = "to-do";' });
  assert.deepEqual(classProblems(root, "", ["to-do"]), []);
});

test("a class inside a template interpolation is checked", () => {
  assert.deepEqual(utilityTokens('const c = `p-2 ${on ? "bg-nope" : "p-1"} ${x}`;'), ["bg-nope"]);
});

test("a class in a template nested in an interpolation is checked", () => {
  assert.deepEqual(utilityTokens("const c = `a ${f(`${g({ k: 1 })} text-nope`)} b`;"), [
    "text-nope",
  ]);
});

test("a template token next to an interpolation is not a class", () => {
  assert.deepEqual(utilityTokens("const c = `bg-red-${n} text-${tone}-500 ring-ok`;"), ["ring-ok"]);
});

test("a lone backtick in a comment does not open a template", () => {
  assert.deepEqual(
    utilityTokens('// a lone ` here\nconst c = "bg-nope";\nconst d = `Size ${n}`;'),
    ["bg-nope"],
  );
  assert.deepEqual(utilityTokens('/* one ` and one \' */ const c = "bg-nope";'), ["bg-nope"]);
});

test("a class named only in a comment is not checked", () => {
  assert.deepEqual(utilityTokens('// bg-comment\n/* text-comment */ const c = "bg-real";'), [
    "bg-real",
  ]);
});

test("two slashes inside a string are not a comment", () => {
  assert.deepEqual(utilityTokens('const u = "https://x.test/a"; const c = "bg-nope";'), [
    "bg-nope",
  ]);
});

test("outline-hidden with a focus-visible width and no style is a hidden outline", () => {
  assert.equal(hiddenFocusOutline("outline-hidden focus-visible:outline-2"), true);
  assert.equal(
    hiddenFocusOutline("outline-hidden focus-visible:outline-2 focus-visible:outline-solid"),
    false,
  );
  assert.equal(hiddenFocusOutline("focus-visible:outline-2"), false);
});

test("a TooltipTrigger without an outline style is reported with its file", () => {
  const root = src({
    "bad.tsx": '<TooltipTrigger className="focus-visible:outline-2 focus-visible:outline-focus">x',
    "good.tsx": '<TooltipTrigger className="focus-visible:outline-2 focus-visible:outline-solid">x',
  });
  assert.equal(focusOutlineProblems(root).length, 1);
  assert.match(focusOutlineProblems(root)[0], /^bad\.tsx: /);
});

test("the project's own TooltipTriggers all draw a focus outline", () => {
  assert.deepEqual(focusOutlineProblems(path.resolve(import.meta.dirname, "..", "src")), []);
});
