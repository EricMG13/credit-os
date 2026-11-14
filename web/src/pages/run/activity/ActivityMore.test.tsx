import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as {
  slice: { current: string | null; runs: { id: string; labels: string[] }[] };
};

function showWith(hash: string, run: unknown) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], run } };
  return render(<App result={result} />);
}
const show = (hash: string) => showWith(hash, fixture.slice);
afterEach(() => {
  window.location.hash = "";
});

const LIVE = ".status-halo, .queued-shimmer, .animate-spin, .feed-rise";
const list = () => within(screen.getByRole("region", { name: "Modules" })).getByRole("list");
const steps = () => within(list()).getAllByRole("listitem");

describe("Run activity, many modules", () => {
  beforeEach(() => show("/run/activity/many-modules"));

  it("draws six steps, two of them collapsed groups", () => {
    expect(steps()).toHaveLength(6);
    expect(screen.getByText("12 modules finished")).toBeTruthy();
    expect(screen.getByText("6 more modules queued")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Show all 12" }).getAttribute("aria-expanded")).toBe(
      "false",
    );
    expect(screen.queryByText("Covenants")).toBeNull();
  });

  it("Show all 12 reveals twelve finished modules and drops the group title", () => {
    fireEvent.click(screen.getByRole("button", { name: "Show all 12" }));
    expect(screen.queryByText("12 modules finished")).toBeNull();
    expect(screen.queryByRole("button", { name: "Show all 12" })).toBeNull();
    expect(steps()).toHaveLength(17);
    expect(screen.getByText("Covenants")).toBeTruthy();
    expect(screen.getByText("Industry and market position")).toBeTruthy();
    expect(screen.getByText("6 more modules queued")).toBeTruthy();
  });

  it("Show all 6 reveals six queued modules", () => {
    fireEvent.click(screen.getByRole("button", { name: "Show all 6" }));
    expect(screen.queryByText("6 more modules queued")).toBeNull();
    expect(steps()).toHaveLength(11);
    expect(screen.getByText("Credit snapshot")).toBeTruthy();
    expect(screen.getByText("12 modules finished")).toBeTruthy();
  });

  it("with both open there are 22 steps and no group", () => {
    fireEvent.click(screen.getByRole("button", { name: "Show all 12" }));
    fireEvent.click(screen.getByRole("button", { name: "Show all 6" }));
    expect(steps()).toHaveLength(22);
    expect(within(list()).queryAllByRole("button")).toHaveLength(0);
  });

  it("the control is a native button and focus lands on the first revealed module's name", () => {
    const button = screen.getByRole("button", { name: "Show all 12" });
    expect(button.tagName).toBe("BUTTON");
    expect(button.getAttribute("type")).toBe("button");
    button.focus();
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    const active = document.activeElement as HTMLElement;
    expect(active.textContent).toBe("Documentation review");
    expect(active.getAttribute("tabindex")).toBe("-1");
    expect(document.body.contains(active)).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Show all 6" }));
    expect((document.activeElement as HTMLElement).textContent).toBe(
      "Pension and lease obligations",
    );
  });
});

describe("Run activity, No run", () => {
  it("none: title, text and the link to the first draft", () => {
    show("/run/activity/none");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Run activity");
    expect(screen.getByText("Runs").tagName).not.toBe("A");
    expect(screen.getByRole("heading", { name: "No run to watch", level: 2 })).toBeTruthy();
    expect(
      screen.getByText(
        "Nothing is running and no run has been started here yet. A run appears on this page as soon as you submit it.",
      ),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: "Start a run" }).getAttribute("href")).toBe(
      "#/run/start/no-documents",
    );
    expect(document.querySelectorAll(LIVE)).toHaveLength(0);
  });

  it("without a draft there is no action", () => {
    const slice = { ...fixture.slice, drafts: [] };
    showWith("/run/activity/none", slice);
    expect(screen.queryByRole("link", { name: "Start a run" })).toBeNull();
  });
});

describe("Run activity, cannot be read", () => {
  beforeEach(() => show("/run/activity/unreadable"));

  it("shows State not known and no run state", () => {
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("TransDigm Group");
    expect(screen.getByText("State not known")).toBeTruthy();
    expect(screen.queryByText("Running")).toBeNull();
    expect(screen.queryByText("Finished")).toBeNull();
    expect(screen.getByText("Full credit review")).toBeTruthy();
  });

  it("the alert has the record's title, text and two links", () => {
    const alert = screen.getByRole("alert");
    expect(within(alert).getByText("Run activity cannot be read")).toBeTruthy();
    expect(
      within(alert).getByText(
        "The run record could not be opened. This does not stop the run or change what it spends; the cap still applies.",
      ),
    ).toBeTruthy();
    expect(within(alert).getByRole("link", { name: "Try again" }).getAttribute("href")).toBe(
      "#/run/activity/unreadable",
    );
    expect(
      within(alert).getByRole("link", { name: "Back to the library" }).getAttribute("href"),
    ).toBe("#/");
  });

  it("draws a static skeleton, no figure and nothing that moves", () => {
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
    expect(document.querySelectorAll(LIVE)).toHaveLength(0);
    expect(
      document.querySelectorAll("[aria-hidden='true'] > .bg-surface-subtle").length,
    ).toBeGreaterThan(0);
    const outside = Array.from(document.querySelectorAll("main *"))
      .filter((el) => el.closest("[role='alert']") === null)
      .map((el) => el.textContent)
      .join(" ");
    expect(outside).not.toContain("USD");
    expect(screen.queryByText("Spend")).toBeNull();
  });
});

describe("Run activity, the group's home address", () => {
  it("/run/activity draws the record current names", () => {
    expect(fixture.slice.current).toBe("running");
    show("/run/activity");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("TransDigm Group");
    expect(screen.getByText("USD 7.40")).toBeTruthy();
    expect(screen.getByText("5 of 13")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Stop run" })).toBeTruthy();
  });

  it("current null draws No run to watch", () => {
    showWith("/run/activity", { ...fixture.slice, current: null });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Run activity");
    expect(screen.getByRole("heading", { name: "No run to watch", level: 2 })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Start a run" }).getAttribute("href")).toBe(
      "#/run/start/no-documents",
    );
  });
});

describe("Run activity, repeated labels", () => {
  it("two identical labels both draw and raise no key warning", () => {
    const warn = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const slice = structuredClone(fixture.slice);
    const run = slice.runs.find((r) => r.id === "running");
    if (run === undefined) throw new Error("fixture has no running run");
    run.labels = ["Full credit review", "Full credit review"];
    showWith("/run/activity/running", slice);
    expect(screen.getAllByText("Full credit review")).toHaveLength(2);
    expect(warn).not.toHaveBeenCalled();
    warn.mockRestore();
  });
});
