import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import {
  defaultAddressProblems,
  domProblems,
  libraryDeclaresHome,
  visitsFor,
} from "./route-visits.mjs";

function withStubGroup(routesSource, body) {
  const root = mkdtempSync(path.join(tmpdir(), "credit-os-visits-"));
  try {
    mkdirSync(path.join(root, "pages", "signal"), { recursive: true });
    mkdirSync(path.join(root, "fixtures"));
    writeFileSync(path.join(root, "pages", "signal", "routes.tsx"), routesSource);
    writeFileSync(
      path.join(root, "fixtures", "signal.json"),
      JSON.stringify({ params: { "/signal/:tab": [{ tab: "a" }] } }),
    );
    body(path.join(root, "pages"), path.join(root, "fixtures"));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

test("a group that declares a home also gets a bare-address visit", () => {
  const source = 'export const routes = [{ path: "/signal/:tab", home: "/signal/a" }];';
  withStubGroup(source, (pages, fixtures) => {
    const { visits, failures } = visitsFor("signal", pages, fixtures);
    assert.deepEqual(failures, []);
    assert.deepEqual(
      visits.map(({ hash, bare }) => [hash, bare]),
      [
        ["#/signal/a", undefined],
        ["#/signal", true],
      ],
    );
  });
});

test("a group with no home gets no bare-address visit", () => {
  withStubGroup('export const routes = [{ path: "/signal/:tab" }];', (pages, fixtures) => {
    assert.deepEqual(
      visitsFor("signal", pages, fixtures).visits.map(({ hash }) => hash),
      ["#/signal/a"],
    );
  });
});

test("Not built yet fails a bare address only; a page may contain those words", () => {
  const dom = "<main><h1>T</h1><p>Not built yet</p></main>";
  assert.deepEqual(domProblems(dom, true), ['the live DOM contains "Not built yet"']);
  assert.deepEqual(domProblems(dom, false), []);
});

test("every visit needs exactly one h1", () => {
  assert.deepEqual(domProblems("<main><h1 class=a>T</h1></main>", false), []);
  assert.deepEqual(domProblems("<main><p>x</p></main>", false), [
    "the live DOM has 0 h1 elements, expected exactly 1",
  ]);
  assert.deepEqual(domProblems("<main><h1>a</h1><h1>b</h1></main>", true), [
    "the live DOM has 2 h1 elements, expected exactly 1",
  ]);
});

test("a failure text and an injected style are reported", () => {
  assert.deepEqual(domProblems("<style><h1>a</h1>Page not found", false), [
    'the live DOM contains "<style"',
    'the live DOM contains "Page not found"',
  ]);
});

test("the default address of a library with a home must be one real page", () => {
  assert.deepEqual(defaultAddressProblems("<main><h1>Library</h1><p>fine</p></main>"), []);
  assert.deepEqual(
    defaultAddressProblems("<main><h1>L</h1><p>Library data is missing</p></main>"),
    ['the live DOM contains "Library data is missing"'],
  );
  assert.deepEqual(defaultAddressProblems("<main><h1>L</h1><p>Not built yet</p></main>"), [
    'the live DOM contains "Not built yet"',
  ]);
  assert.deepEqual(defaultAddressProblems("<div><h1>L</h1></div>"), [
    "the live DOM has 0 main elements, expected exactly 1",
  ]);
});

test("libraryDeclaresHome reads the library group's routes.tsx", () => {
  withStubGroup("export const routes = [];", (pages) => {
    mkdirSync(path.join(pages, "library"));
    writeFileSync(path.join(pages, "library", "routes.tsx"), 'const r = [{ home: "/library/x" }];');
    assert.equal(libraryDeclaresHome(pages), true);
    writeFileSync(path.join(pages, "library", "routes.tsx"), "const r = [];");
    assert.equal(libraryDeclaresHome(pages), false);
  });
});
