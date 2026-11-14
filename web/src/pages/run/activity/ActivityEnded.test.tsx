import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as { slice: unknown };

function show(hash: string) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], run: fixture.slice },
  };
  return render(<App result={result} />);
}
afterEach(() => {
  window.location.hash = "";
});

const LIVE = ".status-halo, .queued-shimmer, .animate-spin, .feed-rise";
const steps = () =>
  within(within(screen.getByRole("region", { name: "Modules" })).getByRole("list"));
const count = (word: string) => steps().getAllByText(word, { selector: "span" }).length;
const head = () => screen.getByRole("heading", { level: 1 }).parentElement?.parentElement;
const link = (name: string) => screen.getByRole("link", { name });

type Case = {
  id: string;
  word: string;
  role: "alert" | "status";
  title: string;
  text: string;
  action: [string, string];
  alt: [string, string] | null;
  shape: string;
};
const CASES: Case[] = [
  {
    id: "failed",
    word: "Failed",
    role: "alert",
    title: "The run failed",
    text: "Financial analysis stopped after three attempts because the model service returned no usable answer. Two modules finished and are kept. Starting again goes through Start and asks before it spends.",
    action: ["Review and start again", "#/run/start/start"],
    alt: ["Open what finished", "#/"],
    shape: "diamond",
  },
  {
    id: "capped",
    word: "Capped",
    role: "status",
    title: "The run reached its USD 20.00 cap",
    text: "Nine modules finished and are in the library. Recovery was stopped part-way and three modules did not run. A new run has its own cap.",
    action: ["Open what finished", "#/"],
    alt: ["Start a new run", "#/run/start/no-documents"],
    shape: "triangle",
  },
  {
    id: "rejected",
    word: "Rejected",
    role: "status",
    title: "The run was rejected before it started",
    text: "One document changed after the summary was approved, so the approval no longer matches what would be read. Nothing was spent.",
    action: ["Back to Documents", "#/run/start/documents"],
    alt: null,
    shape: "cross",
  },
  {
    id: "interrupted",
    word: "Interrupted",
    role: "status",
    title: "The run was interrupted",
    text: "The run stopped at 14:56 while Covenants was running. Five modules finished and are kept. Resuming goes through Start and asks before it spends.",
    action: ["Review and resume", "#/run/start/start"],
    alt: ["Open what finished", "#/"],
    shape: "pause bars",
  },
];

describe.each(CASES)("Run activity, $id", (c) => {
  beforeEach(() => show(`/run/activity/${c.id}`));

  it("says the run state in the heading", () => {
    expect(within(head() as HTMLElement).getByText(c.word)).toBeTruthy();
  });

  it("draws the alert with its title, text, shape and actions", () => {
    const alert = screen.getByRole(c.role);
    expect(within(alert).getByText(c.title, { exact: false }).textContent).toBe(
      `${c.word}: ${c.title}`,
    );
    expect(within(alert).getByText(c.text)).toBeTruthy();
    expect(alert.querySelector(`[data-shape="${c.shape}"]`)).not.toBeNull();
    const first = within(alert).getByRole("link", { name: c.action[0] });
    expect(first.getAttribute("href")).toBe(c.action[1]);
    const links = within(alert).getAllByRole("link");
    expect(links).toHaveLength(c.alt === null ? 1 : 2);
    if (c.alt !== null) {
      expect(within(alert).getByRole("link", { name: c.alt[0] }).getAttribute("href")).toBe(
        c.alt[1],
      );
    }
  });

  it("has no Open the library link, no motion and no Stop run", () => {
    expect(screen.queryByRole("link", { name: "Open the library" })).toBeNull();
    expect(document.querySelectorAll(LIVE)).toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Stop run" })).toBeNull();
  });
});

describe("Run activity, ended modules", () => {
  it("failed: 1 Not assessable and 10 Not run, each Not run saying it did not run", () => {
    show("/run/activity/failed");
    expect(count("Not assessable")).toBe(1);
    expect(count("Not run")).toBe(10);
    expect(steps().getAllByText("Did not run.")).toHaveLength(10);
  });

  it("capped: 1 Not assessable, 3 Not run and a full spend bar", () => {
    show("/run/activity/capped");
    expect(count("Not assessable")).toBe(1);
    expect(count("Not run")).toBe(3);
    const spend = screen.getAllByRole("progressbar")[0] as HTMLElement;
    expect(spend.getAttribute("aria-valuenow")).toBe("20");
    expect(spend.getAttribute("aria-valuemax")).toBe("20");
  });

  it("interrupted: 7 Not run and 1 Interrupted", () => {
    show("/run/activity/interrupted");
    expect(count("Not run")).toBe(7);
    expect(count("Interrupted")).toBe(1);
  });

  it("rejected: no module ran, elapsed n.a., no module list", () => {
    show("/run/activity/rejected");
    expect(screen.getByRole("heading", { name: "No module ran", level: 3 })).toBeTruthy();
    expect(
      screen.getByText(
        "The run was rejected before it started, so there is nothing to show and nothing was spent.",
      ),
    ).toBeTruthy();
    const elapsed = screen.getByText("Elapsed").parentElement as HTMLElement;
    expect(within(elapsed).getByText("n.a.")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Modules" })).queryByRole("list")).toBeNull();
  });
});

describe("Run activity, finished", () => {
  beforeEach(() => show("/run/activity/finished"));

  it("has no alert and the Open the library link in the heading", () => {
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
    expect(link("Open the library").getAttribute("href")).toBe("#/");
    expect(head()?.contains(link("Open the library"))).toBe(true);
  });

  it("keeps Not assessable in place among 12 Finished modules", () => {
    expect(count("Not assessable")).toBe(1);
    expect(count("Finished")).toBe(12);
    expect(document.querySelectorAll(LIVE)).toHaveLength(0);
  });
});

describe("Run activity, figures and trail", () => {
  it("draws the summary figures in the body face, not the display face", () => {
    show("/run/activity/running");
    const figure = screen.getByText("USD 7.40");
    expect(figure.className).toContain("text-metric");
    expect(figure.className).toContain("tabular-nums");
    expect(figure.className).not.toContain("font-display");
  });

  it("gives the Runs trail link a visible focus ring", () => {
    show("/run/activity/running");
    expect(link("Runs").className).toContain("focus-visible:outline-2");
    expect(link("Runs").className).toContain("focus-visible:outline-focus");
  });
});
