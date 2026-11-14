import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, within } from "@testing-library/react";
import { App } from "../../../App";
import type { LoadResult } from "../../../data";

const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../../fixtures/run.json"), "utf8"),
) as { slice: unknown; params: Record<string, Record<string, string>[]> };

function show(hash: string, run: unknown) {
  window.location.hash = `#${hash}`;
  const result: LoadResult = { kind: "ok", data: { schema: "credit-os-data/1", issuers: [], run } };
  return render(<App result={result} />);
}
afterEach(() => {
  window.location.hash = "";
});

const ADDED = "At least one document added";
const READABLE = "Every document can be read";
const PURPOSE = "Purpose chosen";
const APPROVED = "Summary approved";
const SERVICE = "Model service reachable";
const CAP = "Spending cap set";
const SIX = [ADDED, READABLE, PURPOSE, APPROVED, SERVICE, CAP];
type Frame = {
  id: string;
  current: string;
  h2: string;
  states: string[];
  position: string;
  notMet: [string, string[]] | null;
  met: [string, string[]];
  previous: string | null;
  next: string;
  nextTo: string | null;
  blocked: string | null;
};
const NOT_STARTED = "Not started";
const DONE = "Complete";
const NOW = "Current step";
const FRAMES: Frame[] = [
  {
    id: "no-documents",
    current: "Documents",
    h2: "Documents",
    states: [NOW, NOT_STARTED, NOT_STARTED, NOT_STARTED, NOT_STARTED],
    position: "Step 1 of 5",
    notMet: ["4", [ADDED, READABLE, PURPOSE, APPROVED]],
    met: ["2", [SERVICE, CAP]],
    previous: null,
    next: "Next",
    nextTo: null,
    blocked: "Add at least one document to continue.",
  },
  {
    id: "documents",
    current: "Documents",
    h2: "Documents",
    states: [NOW, NOT_STARTED, NOT_STARTED, NOT_STARTED, NOT_STARTED],
    position: "Step 1 of 5",
    notMet: ["3", [READABLE, PURPOSE, APPROVED]],
    met: ["3", [ADDED, SERVICE, CAP]],
    previous: null,
    next: "Next",
    nextTo: null,
    blocked: "Replace or remove the unreadable file to continue.",
  },
  {
    id: "purpose",
    current: "Purpose",
    h2: "Purpose",
    states: [DONE, NOW, NOT_STARTED, NOT_STARTED, NOT_STARTED],
    position: "Step 2 of 5",
    notMet: ["1", [APPROVED]],
    met: ["5", [ADDED, READABLE, PURPOSE, SERVICE, CAP]],
    previous: "#/run/start/documents",
    next: "Next",
    nextTo: "#/run/start/confirm",
    blocked: null,
  },
  {
    id: "confirm",
    current: "Confirm",
    h2: "Confirm what was read",
    states: [DONE, DONE, NOW, NOT_STARTED, NOT_STARTED],
    position: "Step 3 of 5",
    notMet: ["1", [APPROVED]],
    met: ["5", [ADDED, READABLE, PURPOSE, SERVICE, CAP]],
    previous: "#/run/start/purpose",
    next: "Approve summary",
    nextTo: "#/run/start/context",
    blocked: null,
  },
  {
    id: "context",
    current: "More context",
    h2: "More context",
    states: [DONE, DONE, DONE, NOW, NOT_STARTED],
    position: "Step 4 of 5",
    notMet: null,
    met: ["6", SIX],
    previous: "#/run/start/confirm",
    next: "Next",
    nextTo: "#/run/start/start",
    blocked: null,
  },
  {
    id: "start",
    current: "Start",
    h2: "Start",
    states: [DONE, DONE, DONE, DONE, NOW],
    position: "Step 5 of 5",
    notMet: null,
    met: ["6", SIX],
    previous: "#/run/start/context",
    next: "Submit, spend up to USD 20.00",
    nextTo: "#/run/start/started",
    blocked: null,
  },
];

describe.each(FRAMES)("Run start, draft $id", (f) => {
  beforeEach(() => {
    show(`/run/start/${f.id}`, fixture.slice);
  });

  it("marks the current step and says every state in words", () => {
    const steps = within(screen.getByRole("list", { name: "Steps in this run" })).getAllByRole(
      "listitem",
    );
    expect(steps).toHaveLength(5);
    const current = steps.filter((li) => li.getAttribute("aria-current") === "step");
    expect(current).toHaveLength(1);
    expect(current[0]).toHaveTextContent(f.current);
    steps.forEach((li, i) => {
      expect(within(li).getByText(f.states[i] ?? "")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { level: 2, name: f.h2 })).toBeInTheDocument();
  });

  it("draws the readiness counts and items exactly as the slice gave them", () => {
    const panel = screen.getByRole("complementary", { name: "Readiness" });
    expect(within(panel).getByRole("heading", { level: 2, name: "Readiness" })).toBeVisible();
    if (f.notMet === null) {
      expect(within(panel).queryByText("Not met")).toBeNull();
      expect(within(panel).getByText("Everything the run needs is in place.")).toBeVisible();
    } else {
      const list = within(panel).getByRole("list", { name: `Not met ${f.notMet[0]}` });
      expect(
        within(list)
          .getAllByRole("listitem")
          .map((li) => li.textContent),
      ).toEqual(f.notMet[1]);
      expect(
        within(panel).getByText("What still has to be true before the run can start."),
      ).toBeVisible();
    }
    const met = within(panel).getByRole("list", { name: `Met ${f.met[0]}` });
    expect(
      within(met)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(f.met[1]);
    expect(within(panel).getByText("Spending cap for this run")).toBeVisible();
    expect(within(panel).getByRole("progressbar")).toHaveAttribute("aria-valuenow", "0");
    expect(within(panel).getByRole("progressbar")).toHaveAccessibleName("USD 0.00 of USD 20.00");
  });

  it("draws Previous, the position and Next as the slice says", () => {
    expect(screen.getByText(f.position)).toBeVisible();
    if (f.previous === null) {
      expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    } else {
      expect(screen.getByRole("link", { name: "Previous" })).toHaveAttribute("href", f.previous);
    }
    if (f.id === "start") {
      return; // the Submit button and its modal are task 5; only Previous and the position here
    }
    if (f.blocked !== null) {
      const next = screen.getByRole("button", { name: f.next });
      expect(next).toBeDisabled();
      expect(next).toHaveAccessibleDescription(f.blocked);
      expect(screen.getByText(f.blocked)).toBeVisible();
    } else {
      expect(screen.getByRole("link", { name: f.next })).toHaveAttribute("href", f.nextTo);
    }
  });

  it("names no module, step id, hash or file path", () => {
    expect(document.body.textContent).not.toMatch(/CP-\d/);
    const trail = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(trail).getByRole("link", { name: "Library" })).toHaveAttribute("href", "#/");
    expect(trail).toHaveTextContent("Library / TransDigm Group / New run");
    expect(
      screen.getByText(
        "Add the documents, say what the run is for, approve what was read, then start. Nothing is spent before the last step.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Start a run" })).toBeVisible();
  });
});

describe("Run start, draft started", () => {
  beforeEach(() => {
    show("/run/start/started", fixture.slice);
  });
  it("has all five steps complete, none current, and no step actions", () => {
    const steps = within(screen.getByRole("list", { name: "Steps in this run" })).getAllByRole(
      "listitem",
    );
    steps.forEach((li) => {
      expect(li).not.toHaveAttribute("aria-current");
      expect(within(li).getByText("Complete")).toBeInTheDocument();
    });
    expect(screen.queryByText("Previous")).toBeNull();
    expect(screen.queryByText("Step 5 of 5")).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Run started" })).toBeVisible();
  });
});

describe("Run start, addresses the slice does not hold", () => {
  it("says no draft has this address, with one action to Run", () => {
    show("/run/start/nowhere", fixture.slice);
    expect(
      screen.getByRole("heading", { level: 2, name: "No draft has this address" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Go to Run" })).toHaveAttribute("href", "#/run");
    expect(screen.queryByRole("list", { name: "Steps in this run" })).toBeNull();
  });
  it("says there is no run data when the slice is absent", () => {
    show("/run/start/purpose", undefined);
    expect(
      screen.getByRole("heading", { level: 2, name: "No run data in this library" }),
    ).toBeVisible();
    expect(screen.queryByRole("link", { name: "Go to Run" })).toBeNull();
  });
  it("declares a parameter set for every draft of the slice", () => {
    expect(fixture.params["/run/start/:draft"]?.map((s) => s["draft"])).toEqual(
      FRAMES.map((f) => f.id).concat("started"),
    );
  });
});
