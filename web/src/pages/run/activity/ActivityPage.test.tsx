import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as { slice: unknown; params: Record<string, Record<string, string>[]> };

function showWith(hash: string, run: unknown) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], run } };
  return render(<App result={result} />);
}
const show = (hash: string) => showWith(hash, fixture.slice);
afterEach(() => {
  window.location.hash = "";
});

const LIVE_CLASSES = ".status-halo, .queued-shimmer, .animate-spin, .feed-rise";
const STOP_REASON =
  "Not available here: this page shows a saved example and is not connected to the run service.";

const modulesList = () =>
  within(screen.getByRole("region", { name: "Modules" })).queryByRole("list");
const stepsOf = () => within(modulesList() as HTMLElement).getAllByRole("listitem");
const badgeCount = (word: string) =>
  within(modulesList() as HTMLElement).getAllByText(word, { selector: "span" }).length;

describe("Run activity, running", () => {
  beforeEach(() => show("/run/activity/running"));

  it("has one h1 with the issuer, the run state and the labels", () => {
    const h1 = screen.getAllByRole("heading", { level: 1 });
    expect(h1.map((h) => h.textContent)).toEqual(["TransDigm Group"]);
    const head = h1[0]?.parentElement?.parentElement as HTMLElement;
    expect(within(head).getByText("Running")).toBeTruthy();
    expect(within(head).getByText("Full credit review")).toBeTruthy();
    expect(within(head).getByText("As of Q3 FY2026")).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Breadcrumb" }).textContent).toBe(
      "Runs / TransDigm Group",
    );
  });

  it("draws the three summary figures with their bars and note", () => {
    expect(screen.getByText("USD 7.40")).toBeTruthy();
    expect(screen.getByText("5 of 13")).toBeTruthy();
    expect(screen.getByText("16 min 12 s")).toBeTruthy();
    expect(screen.getByText("USD 7.40 of USD 20.00")).toBeTruthy();
    expect(screen.getByText("5 of 13 modules")).toBeTruthy();
    expect(screen.getByText("Started today at 14:38")).toBeTruthy();
    const bars = screen.getAllByRole("progressbar");
    expect(bars.map((b) => b.getAttribute("aria-valuenow"))).toEqual(["7.4", "5"]);
  });

  it("lists the 13 steps in order with one current step", () => {
    const steps = stepsOf();
    expect(steps).toHaveLength(13);
    expect(steps[0]?.textContent).toContain("Documentation review");
    expect(steps[5]?.textContent).toContain("Covenants");
    expect(steps[5]?.textContent).toContain("Started at 14:54");
    expect(steps[12]?.textContent).toContain("Credit snapshot");
    const current = steps.filter((s) => s.getAttribute("aria-current") === "step");
    expect(current).toEqual([steps[5]]);
  });

  it("says each module's state with a badge", () => {
    expect(badgeCount("Finished")).toBe(5);
    expect(badgeCount("Running")).toBe(1);
    expect(badgeCount("Queued")).toBe(7);
  });

  it("shimmers the seven queued steps and pulses the one running badge", () => {
    const steps = stepsOf();
    const shimmering = steps.filter((s) => s.querySelector(".queued-shimmer") !== null);
    expect(shimmering).toHaveLength(7);
    expect(steps[5]?.querySelector(".status-halo")).not.toBeNull();
  });

  it("draws the feed, newest first, with the first line rising in", () => {
    const feed = screen.getByRole("region", { name: "Activity" });
    const lines = within(feed).getAllByRole("article");
    expect(lines).toHaveLength(7);
    expect(lines[0]?.textContent).toContain("Covenants");
    expect(lines[0]?.textContent).toContain("14:54");
    expect(lines[0]?.textContent).toContain("Started.");
    expect(lines[0]?.querySelector("time")?.textContent).toBe("14:54");
    expect(lines[0]?.querySelector("time")?.hasAttribute("datetime")).toBe(false);
    expect(feed.querySelectorAll(".feed-rise")).toHaveLength(1);
    expect(lines[0]?.closest(".feed-rise")).not.toBeNull();
    expect(lines[6]?.textContent).toContain("Started. 13 modules queued, cap USD 20.00.");
  });

  it("disables Stop run and says why", () => {
    const stop = screen.getByRole("button", { name: "Stop run" });
    expect(stop.hasAttribute("disabled")).toBe(true);
    expect(screen.getByText(STOP_REASON)).toBeTruthy();
    expect(stop.getAttribute("aria-describedby")).toBe(screen.getByText(STOP_REASON).id);
  });
});

describe("Run activity, other live states", () => {
  it("queued: elapsed is n.a., not zero, with its line and 13 Queued badges", () => {
    show("/run/activity/queued");
    expect(screen.getByText("Waiting for the model service. Nothing has been spent.")).toBeTruthy();
    expect(screen.getByText("Not started yet")).toBeTruthy();
    const elapsed = screen.getByText("Elapsed").parentElement as HTMLElement;
    expect(within(elapsed).getByText("n.a.")).toBeTruthy();
    expect(badgeCount("Queued")).toBe(13);
    expect(screen.queryByText("Running", { selector: "span" })).toBeNull();
  });

  it("starting: spinner with its label, n.a. finished, no step list", () => {
    show("/run/activity/starting");
    expect(
      screen.getByRole("status", { name: "Starting the run. No module has reported yet." }),
    ).toBeTruthy();
    const done = screen.getByText("Modules finished").parentElement as HTMLElement;
    expect(within(done).getByText("n.a.")).toBeTruthy();
    expect(modulesList()).toBeNull();
    expect(document.querySelectorAll(".animate-spin")).toHaveLength(1);
  });

  it("two Running modules are both current", () => {
    const slice = structuredClone(fixture.slice) as {
      runs: { id: string; modules: { steps: { state: string }[] } }[];
    };
    const steps = slice.runs.find((r) => r.id === "running")?.modules.steps;
    if (steps === undefined) throw new Error("fixture has no running run");
    (steps[6] as { state: string }).state = "Running";
    showWith("/run/activity/running", slice);
    const current = stepsOf().filter((s) => s.getAttribute("aria-current") === "step");
    expect(current).toHaveLength(2);
    expect(badgeCount("Running")).toBe(2);
  });
});

describe("Run activity, ended states", () => {
  it.each(["finished", "failed", "capped", "interrupted", "rejected"])(
    "%s: nothing loops and Stop run is absent",
    (id) => {
      show(`/run/activity/${id}`);
      expect(document.querySelectorAll(LIVE_CLASSES)).toHaveLength(0);
      expect(screen.queryByRole("button", { name: "Stop run" })).toBeNull();
      expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    },
  );

  it("finished: shows its badge and no live word", () => {
    show("/run/activity/finished");
    expect(screen.getAllByText("Finished", { selector: "span" }).length).toBeGreaterThan(0);
    expect(badgeCount("Not assessable")).toBeGreaterThan(0);
  });

  it("rejected: says no module ran", () => {
    show("/run/activity/rejected");
    expect(screen.getByRole("heading", { name: "No module ran", level: 3 })).toBeTruthy();
    expect(modulesList()).toBeNull();
  });
});

describe("Run activity, every address", () => {
  const ids = (fixture.params["/run/activity/:run"] ?? []).map((p) => p["run"]);

  it("the fixture names all eleven runs", () => {
    expect(ids).toEqual([
      "running",
      "queued",
      "starting",
      "finished",
      "failed",
      "capped",
      "rejected",
      "interrupted",
      "many-modules",
      "none",
      "unreadable",
    ]);
  });

  it.each(ids)("%s: one h1 and no module code", (id) => {
    show(`/run/activity/${String(id)}`);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(document.body.textContent).not.toMatch(/CP-\d/);
  });

  it("none: the empty state", () => {
    show("/run/activity/none");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Run activity");
    expect(screen.getByRole("heading", { name: "No run to watch", level: 2 })).toBeTruthy();
  });

  it("unreadable: the issuer and the error alert", () => {
    show("/run/activity/unreadable");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("TransDigm Group");
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Error: ");
  });

  it("an unknown run id says so, with a link back", () => {
    show("/run/activity/nope");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Run activity");
    expect(screen.getByRole("heading", { name: "No run has this address", level: 2 })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Go to Run" }).getAttribute("href")).toBe("#/run");
  });

  it("a slice that is absent still draws one h1", () => {
    showWith("/run/activity/running", undefined);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { name: "No run data in this library" })).toBeTruthy();
  });

  it("a 400-character module detail renders in full", () => {
    const detail = `${"abcdefghi ".repeat(39)}abcdefghij`;
    const slice = structuredClone(fixture.slice) as {
      runs: { id: string; modules: { steps: { detail: string | null }[] } }[];
    };
    const step = slice.runs.find((r) => r.id === "running")?.modules.steps[5];
    if (step === undefined) throw new Error("fixture has no running run");
    step.detail = detail;
    showWith("/run/activity/running", slice);
    expect(detail).toHaveLength(400);
    expect(within(stepsOf()[5] as HTMLElement).getByText(detail)).toBeTruthy();
  });
});
