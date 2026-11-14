import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { routes } from "./routes";

type Json = Record<string, unknown>;

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Json; params: Record<string, Json[]> };

const GAPS = "/library/:issuer/:run/evidence/gaps";
const FULL = "2026-09-30";
const BASE = `#/library/halden-aerostructures/${FULL}`;

function renderGaps(run: string, library: unknown = fixture.slice) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const found = routes.find((r) => r.path === GAPS);
  if (found === undefined) throw new Error("no gaps route");
  return render(
    <SourceContext.Provider value={data}>
      {found.render({ issuer: "halden-aerostructures", run })}
    </SourceContext.Provider>,
  );
}

afterEach(cleanup);

const table = () => screen.getByRole("table", { name: "Gaps" });
const allRows = () => within(table()).getAllByRole("row");
/** The table's rows in order: a group's heading is its severity and count, a gap row its id. */
const outline = () =>
  allRows()
    .slice(1)
    .map((row) => {
      const head = within(row).queryByRole("rowheader");
      return head === null || head.getAttribute("scope") === "rowgroup"
        ? `group ${row.textContent}`
        : head.textContent;
    });
const head = (name: string) => within(table()).getByRole("columnheader", { name });
const rowOf = (id: string) => {
  const found = allRows().find((r) => within(r).queryByRole("rowheader")?.textContent === id);
  if (found === undefined) throw new Error(`no row ${id}`);
  return found;
};

describe("the Gaps route", () => {
  it("is titled Evidence, full bleed, and the fixture visits every run", () => {
    const found = routes.find((r) => r.path === GAPS);
    expect(found?.title).toBe("Evidence");
    expect(found?.layout).toBe("bleed");
    expect(fixture.params[GAPS]?.map((p) => p["run"])).toEqual([
      FULL,
      "2026-06-30",
      "2026-03-31",
      "2025-09-30",
    ]);
  });
});

describe("Evidence, Gaps", () => {
  it("draws the card with the mock's title, delivered count and sentence, with the Gaps tab current", () => {
    renderGaps(FULL);
    expect(screen.getByRole("heading", { name: "Gaps 7" })).toBeVisible();
    expect(
      screen.getByText("What this run could not establish, by how much it bears on the view."),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: /^Gaps/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("region", { name: "Gaps" })).toHaveClass("overflow-x-auto");
  });

  it("keeps the register's region free of a forced width and of focus classes it cannot use", () => {
    renderGaps(FULL);
    const region = screen.getByRole("region", { name: "Gaps" });
    expect(region.className).not.toMatch(/focus|outline/);
    expect(table().className).not.toMatch(/min-w/);
  });

  it("heads each column with scope col, each severity group with scope rowgroup, the sortable columns with aria-sort", () => {
    renderGaps(FULL);
    const heads = within(table()).getAllByRole("columnheader");
    expect(heads.map((h) => h.textContent)).toEqual([
      "Gap",
      "What is missing",
      "Module",
      "Effect on the view",
      "Shown as",
    ]);
    for (const h of heads) expect(h).toHaveAttribute("scope", "col");
    const rowHeads = within(table()).getAllByRole("rowheader");
    const groups = rowHeads.filter((h) => h.getAttribute("scope") === "rowgroup");
    expect(groups.map((h) => h.textContent)).toEqual(["High2", "Medium3", "Low2"]);
    const idCells = rowHeads.filter((h) => h.getAttribute("scope") === "row");
    expect(idCells).toHaveLength(7);
    // An id never breaks inside itself ("G-/01").
    for (const cell of idCells) expect(cell).toHaveClass("whitespace-nowrap");
    expect(head("Gap")).toHaveAttribute("aria-sort", "none");
    expect(head("Module")).toHaveAttribute("aria-sort", "none");
    expect(head("What is missing")).not.toHaveAttribute("aria-sort");
  });

  it("groups the gaps High, Medium, Low with the delivered counts, in the delivered order", () => {
    renderGaps(FULL);
    expect(outline()).toEqual([
      "group High2",
      "G-01",
      "G-02",
      "group Medium3",
      "G-03",
      "G-04",
      "G-05",
      "group Low2",
      "G-06",
      "G-07",
    ]);
  });

  it("draws each gap's words as the mock does", () => {
    renderGaps(FULL);
    const mock: [string, string, string, string][] = [
      [
        "G-01",
        "Security and intercreditor documents",
        "Recovery",
        "Recovery by class is not assessable; the view on the unsecured notes rests on rank alone.",
      ],
      [
        "G-02",
        "Hedge schedule",
        "Capital structure",
        "The fixed and floating split of interest is an estimate; hedge expiries are not drawn.",
      ],
      [
        "G-03",
        "Peer figures on the same basis",
        "Peer comparison",
        "The comparison overstates Halden by an amount the module could not size.",
      ],
      [
        "G-04",
        "Share of revenue under cost pass-through",
        "Business profile",
        "The finding on input costs rests on the margin record, not on contract terms.",
      ],
      [
        "G-05",
        "Average cost of debt",
        "Capital structure",
        "None on the view: interest cover is computed from cash interest paid.",
      ],
      [
        "G-06",
        "EBITDA for 2022 on the current basis",
        "Financial performance",
        "Five-year trends start in 2023.",
      ],
      [
        "G-07",
        "Lease maturity schedule",
        "Capital structure",
        "Leases appear in the debt stack but not by year.",
      ],
    ];
    for (const [id, gap, module, reason] of mock) {
      const cells = within(rowOf(id)).getAllByRole("cell");
      expect(cells.slice(0, 3).map((c) => c.textContent)).toEqual([gap, module, reason]);
    }
  });

  it("draws how each gap appears on the findings pages in the kit's own form", () => {
    renderGaps(FULL);
    expect(within(rowOf("G-01")).getByText("Not assessable")).toBeVisible();
    for (const id of ["G-02", "G-03", "G-04"]) {
      expect(within(rowOf(id)).getByText("Not established for this run")).toBeVisible();
    }
    expect(within(rowOf("G-05")).getByText("Withheld")).toBeVisible();
    for (const id of ["G-06", "G-07"]) expect(within(rowOf(id)).getByText("n.a.")).toBeVisible();
  });

  it("links each gap to the Overview or the module page it sits on", () => {
    renderGaps(FULL);
    expect(within(rowOf("G-01")).getByRole("link")).toHaveAttribute("href", `${BASE}/overview`);
    expect(within(rowOf("G-02")).getByRole("link")).toHaveAttribute(
      "href",
      `${BASE}/modules/capital-structure`,
    );
    expect(within(rowOf("G-06")).getByRole("link")).toHaveAttribute(
      "href",
      `${BASE}/modules/financial-performance`,
    );
  });

  it("sorts the rows inside each group, never the groups", () => {
    renderGaps(FULL);
    fireEvent.click(within(head("Gap")).getByRole("button"));
    fireEvent.click(within(head("Gap")).getByRole("button"));
    expect(head("Gap")).toHaveAttribute("aria-sort", "descending");
    expect(outline()).toEqual([
      "group High2",
      "G-02",
      "G-01",
      "group Medium3",
      "G-05",
      "G-04",
      "G-03",
      "group Low2",
      "G-07",
      "G-06",
    ]);
    fireEvent.click(within(head("Module")).getByRole("button"));
    expect(head("Module")).toHaveAttribute("aria-sort", "ascending");
    expect(head("Gap")).toHaveAttribute("aria-sort", "none");
    expect(outline().slice(4, 7)).toEqual(["G-04", "G-05", "G-03"]);
  });

  it("narrows to one module, drops empty groups and the counts it can no longer vouch for", () => {
    renderGaps(FULL);
    pick("Capital structure");
    expect(outline()).toEqual(["group High", "G-02", "group Medium", "G-05", "group Low", "G-07"]);
    expect(screen.queryByRole("heading", { name: "Gaps 7" })).toBeNull();
    pick("Recovery");
    expect(outline()).toEqual(["group High", "G-01"]);
  });

  it("draws an empty state for a module with no gap, and its way back", () => {
    renderGaps(FULL);
    pick("Industry and competition");
    expect(
      screen.getByRole("heading", { name: "No gap sits in Industry and competition" }),
    ).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Show all gaps" }));
    expect(outline()).toHaveLength(10);
  });

  it("draws the capped run's and the first run's own groups, with no High group where none exists", () => {
    renderGaps("2026-03-31");
    expect(outline()).toEqual(["group High1", "G-01", "group Medium2", "G-02", "G-03"]);
    expect(screen.getByRole("heading", { name: "Gaps 3" })).toBeVisible();
    cleanup();
    renderGaps("2025-09-30");
    expect(outline()).toEqual(["group Medium1", "G-01", "group Low1", "G-02"]);
    expect(screen.queryByRole("columnheader", { name: /^High/ })).toBeNull();
  });

  it("says a run with no gap has none, with no table", () => {
    const slice = structuredClone(fixture.slice) as {
      issuers: { runs: { evidence: { gaps: Json; tabs: Json }; overview: Json }[] }[];
    };
    const run = slice.issuers[0]?.runs[3] as (typeof slice.issuers)[0]["runs"][0];
    run.evidence.gaps["groups"] = [];
    run.evidence.tabs["gaps"] = "0";
    (run.overview["limitations"] as { gapsLink: Json }).gapsLink["label"] =
      "See the 0 gaps in Evidence";
    renderGaps("2025-09-30", slice);
    expect(screen.getByRole("heading", { name: "This run has no gaps" })).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByRole("link", { name: "Gaps0" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps one h1 and no skipped level on every run", () => {
    for (const run of [FULL, "2026-06-30", "2026-03-31", "2025-09-30", "1999-01-01"]) {
      const { container } = renderGaps(run);
      const levels = [...container.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((h) =>
        Number(h.tagName[1]),
      );
      expect(
        levels.filter((l) => l === 1),
        run,
      ).toHaveLength(1);
      levels.forEach((l, i) => {
        if (i > 0) expect(l - (levels[i - 1] ?? 1), run).toBeLessThanOrEqual(1);
      });
      cleanup();
    }
  });
});

/** Chooses a module in the filter through the hidden native select React Aria keeps beside it. */
function pick(name: string) {
  const trigger = screen.getByRole("button", { name: /^Module:/ });
  const select = trigger.closest("div")?.querySelector("select");
  if (!select) throw new Error("no module select");
  fireEvent.change(select, { target: { value: name === "All" ? "all" : `option:${name}` } });
}
