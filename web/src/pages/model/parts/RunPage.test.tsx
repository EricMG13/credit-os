import { act, fireEvent, render, screen, within } from "@testing-library/react";
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

describe("Show sources is session-wide state: it survives route changes and the case resets", () => {
  // The store lives for the session, so each test starts from off through the switch itself.
  beforeEach(() => {
    const { unmount } = open(fixtureSlice(), "#/model/transdigm/2025-06-30/front");
    const sw = screen.getByRole("switch", SWITCH);
    if ((sw as HTMLInputElement).checked) fireEvent.click(sw);
    unmount();
  });

  it("is off by default and on after the analyst turns it on", () => {
    open(fixtureSlice(), "#/model/transdigm/2025-06-30/front");
    expect(screen.getByRole("switch", SWITCH)).not.toBeChecked();
    fireEvent.click(screen.getByRole("switch", SWITCH));
    expect(screen.getByRole("switch", SWITCH)).toBeChecked();
  });

  it("stays on when the address changes to another run on the same tab", () => {
    open(twoRuns({ issuer: "transdigm", run: "2025-12-31" }), "#/model/transdigm/2025-06-30/front");
    fireEvent.click(screen.getByRole("switch", SWITCH));
    go("#/model/transdigm/2025-12-31/front");
    expect(screen.getByRole("switch", SWITCH)).toBeChecked();
  });

  it("stays on when the tab changes", () => {
    open(fixtureSlice(), "#/model/transdigm/2025-06-30/front");
    fireEvent.click(screen.getByRole("switch", SWITCH));
    go("#/model/transdigm/2025-06-30/analysis");
    expect(screen.getByRole("link", { name: "Analysis" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("switch", SWITCH)).toBeChecked();
  });

  it("stays on but resets the case between two runs whose names would join to one string (a/b + c, a + b/c)", () => {
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
    expect(screen.getByRole("switch", SWITCH)).toBeChecked();
    expect(screen.getByRole("radio", { name: /Base case/ })).toBeChecked();
  });
});

describe("An unreadable run's page draws why it could not be read", () => {
  function withBadSecond() {
    const slice = twoRuns({ issuer: "transdigm", run: "2024-12-31" }) as {
      runs: { header: Record<string, unknown> }[];
    };
    must(slice.runs[1]).header["asOf"] = 5;
    return slice;
  }

  it.each(["front", "analysis", "statements", "portfolio-fit", "limitations", "forecast"])(
    "draws the reason on the %s page, with one h1 and the way back",
    (page) => {
      open(withBadSecond(), `#/model/transdigm/2024-12-31/${page}`);
      expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual([
        "Financial model",
      ]);
      expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
      expect(screen.getByText("runs[1].header.asOf: expected a string")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "All financial models" })).toHaveAttribute(
        "href",
        "#/model/runs",
      );
      expect(must(screen.getByRole("main").firstElementChild)).toHaveClass("p-8");
    },
  );

  it("still draws the readable run beside it, and not found for an address naming neither", () => {
    open(withBadSecond(), "#/model/transdigm/2025-06-30/front");
    expect(screen.getByRole("switch", SWITCH)).toBeInTheDocument();
    go("#/model/transdigm/1999-01-01/front");
    expect(
      within(screen.getByRole("main")).getByText("Not found for this run"),
    ).toBeInTheDocument();
  });
});
