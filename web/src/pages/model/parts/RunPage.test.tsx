import { act, fireEvent, render, screen } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { fixtureSlice, must } from "../slice/test-fixture";

type Run = { issuer: string; run: string };

function twoRuns(second: Run): unknown {
  const slice = fixtureSlice() as { runs: Run[] };
  const copy = structuredClone(must(slice.runs[0]));
  copy.issuer = second.issuer;
  copy.run = second.run;
  slice.runs.push(copy);
  return slice;
}

function open(slice: unknown, hash: string) {
  window.location.hash = hash;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

function go(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

const SWITCH = { name: "Show sources" };

describe("Show sources is page-level state and resets on every route change", () => {
  it("is off by default and on after the analyst turns it on", () => {
    open(fixtureSlice(), "#/model/transdigm/2025-06-30/front");
    expect(screen.getByRole("switch", SWITCH)).not.toBeChecked();
    fireEvent.click(screen.getByRole("switch", SWITCH));
    expect(screen.getByRole("switch", SWITCH)).toBeChecked();
  });

  it("turns off when the address changes to another run on the same tab", () => {
    open(twoRuns({ issuer: "transdigm", run: "2025-12-31" }), "#/model/transdigm/2025-06-30/front");
    fireEvent.click(screen.getByRole("switch", SWITCH));
    go("#/model/transdigm/2025-12-31/front");
    expect(screen.getByRole("switch", SWITCH)).not.toBeChecked();
  });

  it("turns off when the tab changes", () => {
    open(fixtureSlice(), "#/model/transdigm/2025-06-30/front");
    fireEvent.click(screen.getByRole("switch", SWITCH));
    go("#/model/transdigm/2025-06-30/analysis");
    expect(screen.getByRole("switch", SWITCH)).not.toBeChecked();
  });

  it("turns off between two runs whose names would join to one string (a/b + c, a + b/c)", () => {
    const slice = fixtureSlice() as { runs: Run[] };
    const first = must(slice.runs[0]);
    first.issuer = "a/b";
    first.run = "c";
    const second = structuredClone(first);
    second.issuer = "a";
    second.run = "b/c";
    slice.runs.push(second);
    open(slice, `#/model/${encodeURIComponent("a/b")}/c/statements`);
    fireEvent.click(screen.getByRole("switch", SWITCH));
    fireEvent.click(screen.getByRole("radio", { name: /Downside case/ }));
    go(`#/model/a/${encodeURIComponent("b/c")}/statements`);
    expect(screen.getByRole("switch", SWITCH)).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /Base case/ })).toBeChecked();
  });
});
