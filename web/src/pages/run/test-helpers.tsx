// Shared set-up for the run page tests: read the run fixture and render the app on it at a hash.
// Test-only: no test's expected value lives here.
import { readFileSync } from "node:fs";
import path from "node:path";
import { render } from "@testing-library/react";
import { App } from "../../App";
import type { LoadResult } from "../../data";

type RunFixture = { slice: unknown; params: Record<string, Record<string, string>[]> };

/** The run fixture file as parsed; a test casts it to the members it reads. */
export function runFixture(): unknown {
  return JSON.parse(
    readFileSync(path.join(import.meta.dirname, "../../../fixtures/run.json"), "utf8"),
  );
}

export const fixture = runFixture() as RunFixture;

/** Renders the app at `hash` with `run` as the slice, whatever it is (an absent slice included). */
export function show(hash: string, run: unknown) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], run } };
  return render(<App result={result} />);
}

/** Renders the app at `hash` with the fixture's own slice. */
export const showFixture = (hash: string) => show(hash, fixture.slice);

// Every run page test starts from its own hash and leaves none behind.
afterEach(() => {
  window.location.hash = "";
});
