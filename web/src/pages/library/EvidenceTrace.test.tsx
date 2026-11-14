import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { routes } from "./routes";

type Json = Record<string, unknown>;
type Row = {
  id: string;
  item: string;
  module: string;
  moduleId: string | null;
  value: { kind: string; at?: number | null } | null;
  sources: string;
  calc: unknown;
};

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Json; params: Record<string, Json[]> };

const TRACE = "/library/:issuer/:run/evidence/trace";
const ITEM = "/library/:issuer/:run/evidence/trace/:item";
const FULL = "2026-09-30";
const rowsOf = (slice: Json = fixture.slice) =>
  (
    (slice["issuers"] as { runs: { evidence: { trace: { rows: Row[] } } | null }[] }[])[0]?.runs[0]
      ?.evidence as { trace: { rows: Row[] } }
  ).trace.rows;

function renderTrace(run: string, item?: string) {
  const data: LibraryData = {
    schema: "credit-os-data/1",
    issuers: fixture.issuers,
    library: fixture.slice,
  };
  const found = routes.find((r) => r.path === (item === undefined ? TRACE : ITEM));
  if (found === undefined) throw new Error("no trace route");
  const params = { issuer: "halden-aerostructures", run, ...(item === undefined ? {} : { item }) };
  return render(
    <SourceContext.Provider value={data}>{found.render(params)}</SourceContext.Provider>,
  );
}

const scrolled = vi.fn();
beforeEach(() => {
  Element.prototype.scrollIntoView = scrolled;
});
afterEach(() => {
  cleanup();
  scrolled.mockReset();
});

const table = () => screen.getByRole("table", { name: "Trace" });
const bodyRows = () =>
  within(table())
    .getAllByRole("row")
    .filter((r) => within(r).queryAllByRole("columnheader").length === 0);
const ids = () => bodyRows().map((r) => within(r).queryByRole("rowheader")?.textContent ?? null);
const head = (name: string) => within(table()).getByRole("columnheader", { name });
const rowOf = (id: string) => {
  const found = bodyRows().find((r) => within(r).queryByRole("rowheader")?.textContent === id);
  if (found === undefined) throw new Error(`no row ${id}`);
  return found;
};
const expander = (id: string) => within(rowOf(id)).getByRole("button");

describe("the Trace routes", () => {
  it("are titled Evidence, full bleed, and the fixture visits each state", () => {
    for (const route of [TRACE, ITEM]) {
      const found = routes.find((r) => r.path === route);
      expect(found?.title).toBe("Evidence");
      expect(found?.layout).toBe("bleed");
    }
    expect(fixture.params[TRACE]?.map((p) => p["run"])).toEqual([
      FULL,
      "2026-06-30",
      "2026-03-31",
      "2025-09-30",
    ]);
    expect(fixture.params[ITEM]?.map((p) => [p["run"], p["item"]])).toEqual([
      [FULL, "T-0014"],
      [FULL, "T-0042"],
      [FULL, "T-9999"],
      ["2026-06-30", "T-0014"],
    ]);
  });
});

describe("Evidence, Trace", () => {
  it("draws the card with the mock's title, delivered count and sentence, in one scroll region", () => {
    renderTrace(FULL);
    expect(screen.getByRole("heading", { name: "Trace 58" })).toBeVisible();
    expect(
      screen.getByText(
        "One row per traced paragraph, row or figure. Open a row to see how it was derived.",
      ),
    ).toBeVisible();
    const region = screen.getByRole("region", { name: "Trace" });
    expect(within(region).getAllByRole("button").length).toBeGreaterThan(0);
    expect(region).toHaveClass("overflow-x-auto");
    expect(screen.getByRole("link", { name: /^Trace/ })).toHaveAttribute("aria-current", "page");
  });

  it("heads each column with the delivered words and a scope, the sortable ones with aria-sort", () => {
    renderTrace(FULL);
    const heads = within(table()).getAllByRole("columnheader");
    expect(heads.map((h) => h.textContent)).toEqual([
      "Derivation",
      "Item",
      "Statement",
      "Value",
      "Module",
      "Kind",
      "Sources",
    ]);
    for (const h of heads) expect(h).toHaveAttribute("scope", "col");
    for (const name of ["Item", "Value", "Module"])
      expect(head(name)).toHaveAttribute("aria-sort", "none");
    for (const name of ["Statement", "Kind", "Sources"])
      expect(head(name)).not.toHaveAttribute("aria-sort");
  });

  it("lists every row in the delivered order, the mock's seven among them as the mock words them", () => {
    renderTrace(FULL);
    expect(ids()).toEqual(rowsOf().map((r) => r.id));
    const mock: [string, string, string, string, string][] = [
      [
        "T-0001",
        "Stable credit with thin headroom: leverage is falling, but the 2028 notes need refinancing.",
        "Overview",
        "Passage",
        "6",
      ],
      ["T-0014", "Net leverage 4.6x", "Capital structure", "Figure", "3"],
      ["T-0015", "Interest cover 2.4x", "Capital structure", "Figure", "4"],
      [
        "T-0031",
        "Three customers bring 58% of revenue and one engine programme 34%.",
        "Business profile",
        "Passage",
        "2",
      ],
      ["T-0047", "Maturities by year", "Capital structure", "Chart", "5"],
      ["T-0052", "Receivables facility availability", "Capital structure", "Row", "1"],
      [
        "T-0068",
        "Management says no alternative part has passed certification.",
        "Business profile",
        "Passage",
        "0",
      ],
    ];
    for (const [id, statement, module, kind, sources] of mock) {
      const cells = within(rowOf(id)).getAllByRole("cell");
      expect(cells.map((c) => c.textContent)).toEqual(
        expect.arrayContaining([expect.stringContaining(statement), module, kind, sources]),
      );
    }
  });

  it("says a figure is not recorded with n.a., and draws the withheld and gap forms", () => {
    renderTrace(FULL);
    expect(within(rowOf("T-0001")).getByText("n.a.")).toBeVisible();
    expect(within(rowOf("T-0014")).getByText("4.6x")).toBeVisible();
    expect(within(rowOf("T-0105")).getByText("Withheld")).toBeVisible();
    expect(within(rowOf("G-02")).getByText("Not established for this run")).toBeVisible();
  });

  it("draws a claim with no calculation as the mock's last row does: no control, a real zero and its note", () => {
    renderTrace(FULL);
    const row = rowOf("T-0068");
    expect(within(row).queryByRole("button")).toBeNull();
    expect(within(row).getByText("0")).toBeVisible();
    expect(within(row).getByText("The module gave no source for this claim.")).toBeVisible();
  });

  it("opens a calculation as the tree the mock draws, and closes it again", () => {
    renderTrace(FULL);
    const button = expander("T-0014");
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(button).toHaveAccessibleName("Show how Net leverage 4.6x was derived");
    expect(screen.queryByRole("list", { name: "How Net leverage 4.6x was derived" })).toBeNull();
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    const tree = screen.getByRole("list", { name: "How Net leverage 4.6x was derived" });
    for (const text of [
      "Result Net leverage",
      "4.6x · C-0412",
      "Formula Net debt ÷ EBITDA",
      "2,236 ÷ 486",
      "Input Net debt = gross debt − cash",
      "2,236 · C-0398",
      "Source Gross debt 2,398",
      "annual-report-2026.pdf · p. 112, note 18",
      "Source Cash 162",
      "annual-report-2026.pdf · p. 84",
      "Input EBITDA, company-adjusted",
      "Source EBITDA 486",
      "lender-presentation-nov-2026.pdf · p. 9",
      "Excerpt “Adjusted EBITDA for the twelve months ended 30 September 2026 was USD 486 million (2025: USD 441 million).”",
    ]) {
      expect(tree.textContent).toContain(text);
    }
    expect(button.getAttribute("aria-controls")).toBe(tree.closest("tr")?.id);
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list", { name: "How Net leverage 4.6x was derived" })).toBeNull();
  });

  it("moves the chevron with no motion under reduced motion", () => {
    renderTrace(FULL);
    expect(expander("T-0014").querySelector("svg")).toHaveClass("motion-reduce:transition-none");
  });

  it("sorts by Item, ascending then descending, by the delivered id", () => {
    renderTrace(FULL);
    const sorted = rowsOf()
      .map((r) => r.id)
      .sort();
    fireEvent.click(within(head("Item")).getByRole("button"));
    expect(head("Item")).toHaveAttribute("aria-sort", "ascending");
    expect(ids()).toEqual(sorted);
    fireEvent.click(within(head("Item")).getByRole("button"));
    expect(head("Item")).toHaveAttribute("aria-sort", "descending");
    expect(ids()).toEqual([...sorted].reverse());
    expect(head("Module")).toHaveAttribute("aria-sort", "none");
  });

  it("sorts by Module by the delivered name", () => {
    renderTrace(FULL);
    const names = rowsOf()
      .map((r) => r.module)
      .sort();
    fireEvent.click(within(head("Module")).getByRole("button"));
    expect(ids().map((id) => rowsOf().find((r) => r.id === id)?.module)).toEqual(names);
    fireEvent.click(within(head("Module")).getByRole("button"));
    expect(ids().map((id) => rowsOf().find((r) => r.id === id)?.module)).toEqual(
      [...names].reverse(),
    );
  });

  it("sorts by Value by the figure's own sort key and leaves a missing one last either way", () => {
    renderTrace(FULL);
    const keyed = rowsOf().filter(
      (r) => r.value?.kind === "value" && typeof r.value.at === "number",
    );
    const unkeyed = rowsOf().length - keyed.length;
    const at = (id: string) => {
      const v = rowsOf().find((r) => r.id === id)?.value;
      return v?.kind === "value" && typeof v.at === "number" ? v.at : null;
    };
    for (const [clicks, way] of [
      [1, 1],
      [2, -1],
    ] as const) {
      cleanup();
      renderTrace(FULL);
      for (let i = 0; i < clicks; i += 1)
        fireEvent.click(within(head("Value")).getByRole("button"));
      const order = ids().map((id) => at(id ?? ""));
      const present = order.slice(0, keyed.length);
      expect(present.every((n) => n !== null)).toBe(true);
      expect(order.slice(keyed.length)).toEqual(Array<null>(unkeyed).fill(null));
      expect(present).toEqual([...present].sort((a, b) => way * ((a ?? 0) - (b ?? 0))));
    }
  });

  it("keeps a row open when the table is sorted", () => {
    renderTrace(FULL);
    fireEvent.click(expander("T-0014"));
    fireEvent.click(within(head("Module")).getByRole("button"));
    expect(expander("T-0014")).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("list", { name: "How Net leverage 4.6x was derived" })).toBeVisible();
    fireEvent.click(within(head("Item")).getByRole("button"));
    expect(screen.getByRole("list", { name: "How Net leverage 4.6x was derived" })).toBeVisible();
  });

  it("opens at an address: that row open, scrolled into view and focused", () => {
    renderTrace(FULL, "T-0014");
    expect(expander("T-0014")).toHaveAttribute("aria-expanded", "true");
    expect(expander("T-0014")).toHaveFocus();
    expect(scrolled).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("opens at the address of a row with no calculation: the row is focused and nothing opens", () => {
    renderTrace(FULL, "T-0042");
    expect(rowOf("T-0042")).toHaveFocus();
    expect(rowOf("T-0042")).toHaveAttribute("tabindex", "-1");
    expect(expander("T-0014")).toHaveAttribute("aria-expanded", "false");
    expect(scrolled).toHaveBeenCalledTimes(1);
  });

  it("opens at an address no item has: the whole table and a warning, nothing opened or focused", () => {
    renderTrace(FULL, "T-9999");
    expect(screen.getByRole("alert")).toHaveTextContent("No item has this address");
    expect(ids()).toEqual(rowsOf().map((r) => r.id));
    expect(expander("T-0014")).toHaveAttribute("aria-expanded", "false");
    expect(scrolled).not.toHaveBeenCalled();
    expect(table().contains(document.activeElement)).toBe(false);
  });

  const pick = (name: string) => {
    const trigger = screen.getByRole("button", { name: /^Module:/ });
    const select = trigger.closest("div")?.querySelector("select");
    if (!select) throw new Error("no module select");
    fireEvent.change(select, { target: { value: name === "All" ? "all" : `option:${name}` } });
  };

  it("narrows the table to one module, and drops the count it can no longer vouch for", () => {
    renderTrace(FULL);
    pick("Recovery");
    expect(ids()).toEqual(
      rowsOf()
        .filter((r) => r.moduleId === "recovery")
        .map((r) => r.id),
    );
    expect(screen.queryByRole("heading", { name: "Trace 58" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Trace" })).toBeVisible();
    pick("All");
    expect(ids()).toHaveLength(58);
  });

  it("draws an empty state for a module no item sits in, and its way back", () => {
    renderTrace(FULL);
    const held = new Set(rowsOf().map((r) => r.moduleId));
    expect(held.has("industry-and-competition")).toBe(false);
    pick("Industry and competition");
    expect(
      screen.getByRole("heading", { name: "No traced item sits in Industry and competition" }),
    ).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Show all items" }));
    expect(ids()).toHaveLength(58);
  });

  it("draws an empty state for a run that traces nothing, with the delivered count", () => {
    renderTrace("2026-03-31");
    expect(screen.getByRole("heading", { name: "Nothing is traced in this run" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Trace0" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("keeps one h1 and no skipped level in every state", () => {
    const states: [string, string | undefined][] = [
      [FULL, undefined],
      [FULL, "T-0014"],
      [FULL, "T-9999"],
      ["2026-03-31", undefined],
      ["2026-06-30", "T-0014"],
      ["1999-01-01", undefined],
    ];
    for (const [run, item] of states) {
      const { container } = renderTrace(run, item);
      const levels = [...container.querySelectorAll("h1,h2,h3,h4,h5,h6")].map((h) =>
        Number(h.tagName[1]),
      );
      expect(
        levels.filter((l) => l === 1),
        `${run} ${item ?? ""}`,
      ).toHaveLength(1);
      levels.forEach((l, i) => {
        if (i > 0) expect(l - (levels[i - 1] ?? 1), `${run} ${item ?? ""}`).toBeLessThanOrEqual(1);
      });
      cleanup();
    }
  });
});
