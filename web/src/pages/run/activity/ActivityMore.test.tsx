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

const GROUP =
  "6 more modules queued, each one starting only once the module before it has finished running";
const LIVE = ".status-halo, .queued-shimmer, .animate-spin, .feed-rise";
const list = () => within(screen.getByRole("region", { name: "Modules" })).getByRole("list");
const steps = () => within(list()).getAllByRole("listitem");

describe("Run activity, many modules", () => {
  beforeEach(() => show("/run/activity/many-modules"));

  it("draws six steps, two of them collapsed groups", () => {
    expect(steps()).toHaveLength(6);
    expect(screen.getByText("12 modules finished")).toBeTruthy();
    expect(screen.getByText(GROUP)).toBeTruthy();
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
    expect(screen.getByText(GROUP)).toBeTruthy();
  });

  it("Show all 6 reveals six queued modules", () => {
    fireEvent.click(screen.getByRole("button", { name: "Show all 6" }));
    expect(screen.queryByText(GROUP)).toBeNull();
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
    expect(button).toHaveClass("font-semibold", "text-brand-secondary");
    expect(button.className).toContain("outline-brand");
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

describe("Run activity, long text from the fixture", () => {
  beforeEach(() => show("/run/activity/many-modules"));

  it("draws the long label, module name and group title in full, cut by nothing", () => {
    const label = "Full credit review with every optional module and a late cut-off";
    const name =
      "Environmental, social and governance factors, with supplier, customer and regulatory exposure";
    for (const text of [label, name, GROUP]) {
      const el = screen.getByText(text);
      expect(el).toBeVisible();
      expect(el.className).not.toMatch(/truncate|line-clamp|text-ellipsis/);
    }
    // the module name and group title sit in text that may wrap
    expect(screen.getByText(name).className).not.toContain("whitespace-nowrap");
    expect(screen.getByText(GROUP).className).not.toContain("whitespace-nowrap");
  });

  it("draws the two long feed lines in full", () => {
    const feed = within(screen.getByRole("region", { name: "Activity" }));
    expect(
      feed.getByText(
        "Finished the review of the credit agreement and its latest amendment, then compared the stated leverage tests with the quarterly report and the segment data. Two tests were read from the amendment itself and one from its summary table, and each is stated with its period so a reader can see which was tested and when.",
      ),
    ).toBeVisible();
    expect(
      feed.getByText(
        "Stopped to wait for the model service, then carried on once it answered. The module that was waiting kept every figure it had already read, so nothing was read twice, and the time spent waiting counts in the elapsed time shown above, not in the spend. The run did not need to start the module again.",
      ),
    ).toBeVisible();
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

  it("draws the Runs trail the other run records draw", () => {
    const trail = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(trail).getByRole("link", { name: "Runs" }).getAttribute("href")).toBe("#/run");
    expect(trail.textContent).toBe("Runs / TransDigm Group");
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
