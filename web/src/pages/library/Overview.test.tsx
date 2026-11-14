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

const PATH = "/library/:issuer/:run/overview";

function renderOverview(
  run: string,
  library: unknown = fixture.slice,
  issuer = "halden-aerostructures",
) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === PATH);
  if (route === undefined) throw new Error("no overview route");
  return render(
    <SourceContext.Provider value={data}>{route.render({ issuer, run })}</SourceContext.Provider>,
  );
}

const tiles = () =>
  within(screen.getByRole("region", { name: "Headline figures" })).getAllByRole("listitem");
const traces = () =>
  screen.queryAllByRole("button", {
    name: /^Show sources for (the bottom line|this figure|this point)$/,
  });

describe("the overview route", () => {
  it("is titled Overview and the fixture visits the full, loading, capped and first runs", () => {
    expect(routes.find((r) => r.path === PATH)?.title).toBe("Overview");
    expect(fixture.params[PATH]?.map((p) => p["run"])).toEqual([
      "2026-09-30",
      "2026-06-30",
      "2026-03-31",
      "2025-09-30",
    ]);
  });
});

describe("Overview, the mock's run", () => {
  it("draws the bottom line band: label, lead as an h2, the rest and one trace control", () => {
    renderOverview("2026-09-30");
    const band = screen.getByRole("region", { name: "Bottom line" });
    expect(within(band).getByText("Bottom line")).toBeVisible();
    expect(
      within(band).getByRole("heading", {
        level: 2,
        name: "Stable credit with thin headroom: leverage is falling, but the 2028 notes need refinancing before the engine programme pays back.",
      }),
    ).toBeVisible();
    expect(within(band).getByText(/^Halden converts a strong order book/)).toBeVisible();
    expect(
      within(band).getByRole("button", { name: "Show sources for the bottom line" }),
    ).toBeVisible();
  });

  it("draws six headline tiles with the mock's labels, figures and notes", () => {
    renderOverview("2026-09-30");
    expect(tiles().map((tile) => tile.textContent)).toEqual([
      "Revenue, USD m2,105Year to 30 Sep 2026",
      "EBITDA margin23.1%Company-adjusted basis",
      "Net leverage4.6xNet debt to EBITDA",
      "Interest cover2.4xEBITDA to cash interest",
      "Liquidity, USD m412Cash and undrawn facility",
      "Recovery, senior notesn.a.not availableRecovery was not assessable",
    ]);
    expect(within(tiles()[5] as HTMLElement).getByText("n.a.").parentElement).toHaveClass(
      "text-text-tertiary",
    );
    expect(within(tiles()[5] as HTMLElement).queryByRole("button")).toBeNull();
  });

  it("draws For and against: h2, its note, two h3 columns of three tiles each", () => {
    renderOverview("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "For and against" })).toBeVisible();
    expect(
      screen.getByText("Three points on each side, as the modules weighed them"),
    ).toBeVisible();
    const sides = within(screen.getByRole("region", { name: "For and against" })).getAllByRole(
      "heading",
      { level: 3 },
    );
    expect(sides.map((h) => h.textContent)).toEqual(["Supports the view", "Against the view"]);
    const against = within(sides[1]?.parentElement as HTMLElement).getAllByRole("listitem");
    expect(against.map((item) => item.textContent)).toEqual([
      "USD 310mUnsecured notes fall due in 2028 with no refinancing agreed and coupons likely to reset higher.Reported",
      "2.4xInterest cover leaves little room if floating rates stay where they are.Unhedged portion estimated",
      "34%Revenue from one engine programme whose ramp has slipped twice.Management disclosure",
    ]);
    expect(
      within(sides[0]?.parentElement as HTMLElement).getAllByRole("listitem")[0]?.textContent,
    ).toBe(
      "4.6xNet leverage fell from 4.9x a year earlier as EBITDA grew faster than debt.Reported",
    );
  });

  it("never skips a heading level under the frame's h1", () => {
    renderOverview("2026-09-30");
    expect(screen.getAllByRole("heading").map((h) => h.tagName)).toEqual([
      "H1",
      "H2",
      "H2",
      "H3",
      "H3",
      "H2",
      "H2",
      "H2",
      "H3",
      "H3",
      "H3",
      "H3",
      "H2",
      "H2",
    ]);
  });

  it("draws one trace control per traced figure: the band, five metrics, six points", () => {
    renderOverview("2026-09-30");
    expect(traces()).toHaveLength(12);
    for (const tile of tiles().slice(0, 5))
      expect(within(tile).getAllByRole("button")).toHaveLength(1);
  });

  it("opens the trace drawer of the figure whose control is pressed", () => {
    renderOverview("2026-09-30");
    fireEvent.click(within(tiles()[2] as HTMLElement).getByRole("button"));
    expect(screen.getByRole("dialog", { name: "Sources for net leverage" })).toBeVisible();
  });

  it("turns every control on with Show sources", () => {
    const { container } = renderOverview("2026-09-30");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "on");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
  });

  it("shows no audit material: ids, files, hashes, run codes or module timings", () => {
    const { container } = renderOverview("2026-09-30");
    const all = [container.innerHTML, container.textContent].join(" ");
    expect(all).not.toMatch(/T-\d{4}|C-\d{4}|\.pdf|hash|run code|net-leverage|interest-cover/i);
    expect(all).not.toMatch(/\d+ ?ms|seconds/i);
  });
});

describe("Overview, states", () => {
  it("draws the loading run as a skeleton only", () => {
    const { container } = renderOverview("2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("region", { name: "Bottom line" })).toBeNull();
    expect(traces()).toHaveLength(0);
  });

  it("draws a zero as 0, a withheld figure as Withheld, a gap and a missing figure apart", () => {
    renderOverview("2026-03-31");
    const [zero, withheld, gap, missing] = tiles() as [
      HTMLElement,
      HTMLElement,
      HTMLElement,
      HTMLElement,
    ];
    expect(within(zero).getByText("0")).toBeVisible();
    expect(within(zero).queryByText("n.a.")).toBeNull();
    expect(within(withheld).getByText("Withheld")).toBeVisible();
    expect(
      within(withheld).getByText("Withheld until the financial performance module is delivered"),
    ).toBeVisible();
    expect(within(gap).getByText("Not established for this run")).toBeVisible();
    expect(within(gap).getByText("No net debt figure was delivered before the cap.")).toBeVisible();
    expect(within(missing).getByText("n.a.")).toBeVisible();
    expect(traces()).toHaveLength(0);
  });

  it("draws a long point in full, and a missing figure in a point as n.a.", () => {
    renderOverview("2026-03-31");
    const long = screen.getByText(
      /^The financial performance, cash flow, recovery and forecast modules/,
    );
    expect(long.textContent).toMatch(/that did run\.$/);
    expect(long).not.toHaveClass("truncate");
    expect(within(long.closest("li") as HTMLElement).getByText("n.a.")).toBeVisible();
    expect(within(long.closest("li") as HTMLElement).getByText("Not run")).toBeVisible();
  });

  it("says which part is missing for a run or an issuer the slice does not hold", () => {
    renderOverview("1999-01-01");
    expect(screen.getByText("No such run")).toBeVisible();
  });

  it("says no such issuer, with the way back to the library", () => {
    renderOverview("2026-09-30", fixture.slice, "nobody");
    expect(screen.getByText("No such issuer")).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toBeVisible();
  });
});

describe("Overview, fix round 1", () => {
  it("draws the section heading in the system h2 size and the bottom-line lead in h2", () => {
    renderOverview("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "For and against" })).toHaveClass(
      "text-h2",
    );
    expect(screen.getByRole("heading", { level: 2, name: /^Stable credit/ })).toHaveClass(
      "text-h3",
    );
  });

  it("lets a point tile hold at narrow widths: container, stacks until wide, figure and badge shrink", () => {
    renderOverview("2026-09-30");
    const item = screen.getByText("Unhedged portion estimated").closest("li") as HTMLElement;
    expect(item).toHaveClass("@container");
    const row = screen.getByText(/^Interest cover leaves little room/).parentElement?.parentElement;
    expect(row).toHaveClass("flex-col", "@md:flex-row");
    const figure = within(item).getByText("2.4x").parentElement as HTMLElement;
    expect(figure.className).not.toMatch(/(^| )w-50/);
    expect(screen.getByText("Unhedged portion estimated")).toHaveClass(
      "whitespace-normal",
      "max-w-full",
    );
  });

  it("puts no block element inside a phrasing span, and logs no React error", () => {
    const errors: string[] = [];
    const spy = vi.spyOn(console, "error").mockImplementation((...args: unknown[]) => {
      errors.push(args.join(" "));
    });
    const { container } = renderOverview("2026-03-31");
    spy.mockRestore();
    expect([...container.querySelectorAll("span div, span p")]).toEqual([]);
    expect(errors).toEqual([]);
  });

  it("draws the n.a. at the figure's size and regular weight, in both users of a figure", () => {
    const holders = (na: HTMLElement, host: HTMLElement) => {
      const chain: HTMLElement[] = [];
      for (let el: HTMLElement | null = na; el !== null && el !== host; el = el.parentElement)
        chain.push(el);
      return chain;
    };
    renderOverview("2026-09-30");
    const metric = tiles()[5] as HTMLElement;
    const cases: [HTMLElement, HTMLElement, string][] = [
      [within(metric).getByText("n.a."), metric, "text-[30px]/[38px]"],
    ];
    cleanup();
    renderOverview("2026-03-31");
    const point = screen
      .getByText(/^The financial performance, cash flow, recovery and forecast modules/)
      .closest("li") as HTMLElement;
    cases.push([within(point).getByText("n.a."), point, "text-[40px]/11"]);
    for (const [na, host, size] of cases) {
      const chain = holders(na, host);
      expect(chain.some((el) => el.classList.contains(size))).toBe(true);
      expect(chain.some((el) => el.classList.contains("font-normal"))).toBe(true);
      expect(chain.filter((el) => el.classList.contains("font-semibold"))).toEqual([]);
    }
  });

  it("says the capped run's points come from the delivered modules", () => {
    renderOverview("2026-03-31");
    expect(screen.getByText(/^Points taken from the nine delivered modules only/)).toBeVisible();
  });
});

describe("Overview, findings, what would change the view and dates", () => {
  const findings = () =>
    within(screen.getByRole("region", { name: "Key findings" })).getAllByRole("listitem");

  it("draws the mock's five findings: delivered number, 600-weight lead, 16/26 body", () => {
    renderOverview("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "Key findings" })).toBeVisible();
    expect(findings().map((item) => item.textContent)).toEqual([
      "01Deleveraging is real but slowLeverage fell by 0.3x in the year. Almost all of it came from EBITDA growth; net debt rose after the Corvane Fasteners purchase.",
      "02Cash conversion lags marginWorking capital absorbed USD 71m as inventory was built for the engine ramp. Free cash flow covered interest but little else.",
      "03Pricing power sits in the aftermarketSole-source parts carry most of the profit. Original-equipment contracts are fixed-price and thinner than peers.",
      "04The 2028 notes are the first real testThe term loan and secured notes run to 2030 and 2031. The unsecured notes come first and rank behind both.",
      "05Documentation is permissiveOnly a springing first-lien covenant applies, and only when the facility is more than 40% drawn. It is far from tested.",
    ]);
    const lead = screen.getByText("Deleveraging is real but slow");
    expect(lead).toHaveClass("font-semibold", "text-body");
    expect(screen.getByText(/^Leverage fell by 0.3x/)).toHaveClass("text-body");
  });

  it("gives every finding and the triggers note exactly one trace control, with the mock's names", () => {
    renderOverview("2026-09-30");
    for (const item of findings()) {
      expect(
        within(item).getAllByRole("button", { name: "Show sources for this finding" }),
      ).toHaveLength(1);
    }
    const view = screen.getByRole("region", { name: "What would change the view" });
    expect(within(view).getAllByRole("button")).toHaveLength(1);
    expect(
      within(view).getByRole("button", { name: "Show sources for the triggers" }),
    ).toBeVisible();
  });

  it("opens the trace of a finding", () => {
    renderOverview("2026-09-30");
    fireEvent.click(within(findings()[1] as HTMLElement).getByRole("button"));
    expect(screen.getByRole("dialog", { name: "Sources for cash conversion" })).toBeVisible();
  });

  it("draws what would change the view as an info note under its h2", () => {
    renderOverview("2026-09-30");
    expect(
      screen.getByRole("heading", { level: 2, name: "What would change the view" }),
    ).toBeVisible();
    const note = screen.getByRole("note");
    expect(within(note).getByText("Two triggers, either is enough")).toBeVisible();
    expect(
      within(note).getByText(
        "Net leverage back above 5.0x at a year end, or no refinancing of the 2028 unsecured notes agreed by 30 June 2027. Either would move the view to negative.",
      ),
    ).toBeVisible();
  });

  it("draws the four dates with their state words, shapes that differ by state, and no trace", () => {
    renderOverview("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "Dates to watch" })).toBeVisible();
    const dates = within(screen.getByRole("region", { name: "Dates to watch" })).getAllByRole(
      "listitem",
    );
    expect(dates.map((item) => item.textContent)).toEqual([
      "12 Nov 2026PastFull-year resultsPublished; figures in this run are from them.",
      "11 Feb 2027NextFirst-quarter resultsFirst read on engine deliveries and inventory release.",
      "30 Jun 2027LaterRefinancing milestoneOur date for an agreed refinancing of the 2028 notes.",
      "15 Mar 2028LaterUnsecured notes matureUSD 310m falls due.",
    ]);
    const mark = (item: HTMLElement) => item.querySelector("svg")?.outerHTML;
    expect(
      new Set([
        mark(dates[0] as HTMLElement),
        mark(dates[1] as HTMLElement),
        mark(dates[2] as HTMLElement),
      ]).size,
    ).toBe(3);
    expect(mark(dates[2] as HTMLElement)).toBe(mark(dates[3] as HTMLElement));
    for (const item of dates) expect(within(item).queryByRole("button")).toBeNull();
  });

  it("sets findings left of the note and dates from the large width, stacked below it", () => {
    renderOverview("2026-09-30");
    const grid = screen.getByRole("heading", { name: "Key findings" }).closest(".grid");
    expect(grid).toHaveClass("grid-cols-1", "lg:grid-cols-[minmax(0,1fr)_360px]");
  });

  it("draws the capped run's lower half with no trace control", () => {
    renderOverview("2026-03-31");
    expect(findings()).toHaveLength(2);
    expect(screen.getByText("Not yet formed")).toBeVisible();
    expect(screen.queryAllByRole("button", { name: /^Show sources for/ })).toHaveLength(0);
    expect(
      within(screen.getByRole("region", { name: "Dates to watch" })).getAllByRole("listitem"),
    ).toHaveLength(2);
  });
});

describe("Overview, modules and limitations", () => {
  const items = () =>
    within(screen.getByRole("region", { name: "Modules" })).getAllByRole("listitem");
  const BASE = "#/library/halden-aerostructures/";

  it("draws the modules heading, the delivered summary and the mock's thirteen items", () => {
    renderOverview("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "Modules" })).toBeVisible();
    expect(screen.getByText("12 of 13 delivered")).toBeVisible();
    expect(items()).toHaveLength(13);
    expect(items()[4]?.textContent).toBe(
      "Capital structureSecured debt is long-dated; the unsecured notes mature first.Delivered with gaps",
    );
    expect(items()[8]?.textContent).toBe(
      "RecoveryThe security package documents were not among the files provided, so recovery by class could not be assessed.Not assessable",
    );
    expect(items()[0]?.textContent).toMatch(/Delivered$/);
  });

  it("links each module item to its module page, in two columns", () => {
    renderOverview("2026-09-30");
    expect(within(items()[4] as HTMLElement).getByRole("link")).toHaveAttribute(
      "href",
      `${BASE}2026-09-30/modules/capital-structure`,
    );
    expect(screen.getAllByRole("link", { name: /^Recovery/ })).toHaveLength(1);
    const lists = within(screen.getByRole("region", { name: "Modules" })).getAllByRole("list");
    expect(lists).toHaveLength(2);
    expect(lists[0]?.parentElement).toHaveClass("grid-cols-1", "md:grid-cols-2");
    expect(lists.map((list) => list.children.length)).toEqual([7, 6]);
    for (const list of lists) {
      for (const row of Array.from(list.children)) {
        // The rule is dropped by a `last:` utility alone, so only a column's last row loses it.
        expect(row.className.split(" ").filter((c) => c.includes("border-b"))).toEqual([
          "last:[&>*]:border-b-0",
        ]);
        expect(row.firstElementChild).toHaveClass("border-b");
        expect(row.firstElementChild).not.toHaveClass("border-b-0");
      }
    }
  });

  it("collapses a repeated state into one plain item with its names and a chevron", () => {
    renderOverview("2026-03-31");
    expect(items().map((item) => item.querySelector("a") === null)).toEqual([
      true,
      false,
      false,
      false,
      false,
      false,
      false,
    ]);
    expect(items()[0]?.textContent).toBe(
      "7 modules deliveredBusiness profile, Industry and competition, Covenants and documentation, Management and governance, Rating outlook, Environmental, social and governance, Credit snapshot.Delivered",
    );
    const chevrons = (item: HTMLElement | undefined) =>
      item?.querySelectorAll("svg[aria-hidden='true'].text-text-tertiary").length;
    expect(items().map(chevrons)).toEqual([1, 0, 0, 0, 0, 0, 0]);
  });

  it("draws the capped run's modules as its own story: nine delivered, four not run", () => {
    renderOverview("2026-03-31");
    expect(screen.getByText("9 of 13 delivered")).toBeVisible();
    expect(items()).toHaveLength(7);
    expect(items()[0]).toHaveTextContent("7 modules delivered");
    for (const title of [
      "Financial performance",
      "Cash flow and liquidity",
      "Recovery",
      "Forecast",
    ]) {
      const item = items().find((el) => el.textContent.startsWith(title)) as HTMLElement;
      expect(within(item).getByText("Not run")).toBeVisible();
      expect(within(item).queryByText("Not assessable")).toBeNull();
    }
    expect(screen.queryByText(/security package documents|documents were not/)).toBeNull();
    expect(screen.queryByText("Not assessable")).toBeNull();
  });

  it("agrees across the capped run's fixture: counts equal names, the text names the not-run modules", () => {
    type Capped = {
      head: { tabs: { modulesCount: string } };
      overview: {
        modules: { summary: string; items: { title: string; lead: string; state: string }[] };
      };
    };
    const capped = (
      fixture.slice as { issuers: { id: string; runs: ({ id: string } & Capped)[] }[] }
    ).issuers
      .find((i) => i.id === "halden-aerostructures")
      ?.runs.find((r) => r.id === "2026-03-31") as Capped;
    const run = capped.overview;
    const [collapsed, ...rest] = run.modules.items;
    const named = (collapsed?.lead ?? "").replace(/\.$/, "").split(/, (?=[A-Z])/).length;
    expect(collapsed?.title).toBe(`${String(named)} modules delivered`);
    const delivered = rest.filter((m) => m.state.startsWith("Delivered")).length;
    expect(run.modules.summary).toBe(`${String(named + delivered)} of 13 delivered`);
    const notRun = run.modules.items.filter((m) => m.state === "Not run").map((m) => m.title);
    expect(notRun).toEqual([
      "Financial performance",
      "Cash flow and liquidity",
      "Recovery",
      "Forecast",
    ]);
    // Sweep ruling SW-01: the Modules tab counts the modules the run lists (as the mock's "Modules 13"
    // beside "12 of 13 delivered"), here the delivered ones and the four not run.
    expect(capped.head.tabs.modulesCount).toBe(String(named + delivered + notRun.length));
  });

  it("draws the limitations open: h2 with count, gaps link, one trace control each, long text in full", () => {
    renderOverview("2026-09-30");
    const region = screen.getByRole("region", { name: "Limitations" });
    expect(within(region).getByRole("heading", { level: 2 }).textContent).toBe("Limitations4");
    expect(
      within(region).getByRole("link", { name: "See the 7 gaps in Evidence" }),
    ).toHaveAttribute("href", `${BASE}2026-09-30/evidence/gaps`);
    const rows = within(region).getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    for (const row of rows) {
      expect(
        within(row).getAllByRole("button", { name: "Show sources for this limitation" }),
      ).toHaveLength(1);
    }
    const long = within(region).getByText(/^Peer figures for two companies/);
    expect(long.textContent).toMatch(/could not size\.$/);
    expect(long).not.toHaveClass("truncate");
  });

  it("collapses and expands the limitations from one button and prints them open", () => {
    renderOverview("2026-09-30");
    const region = screen.getByRole("region", { name: "Limitations" });
    fireEvent.click(within(region).getByRole("button", { name: "Collapse limitations" }));
    expect(within(region).queryByRole("listitem")).toBeNull();
    expect(within(region).getByRole("button", { name: "Expand limitations" })).toBeVisible();
    expect(region.querySelector("[role='group']")).toHaveClass("print:block");
    fireEvent.click(within(region).getByRole("button", { name: "Expand limitations" }));
    expect(within(region).getAllByRole("listitem")).toHaveLength(4);
  });

  it("draws the capped run's limitations with no trace control and its long sentence in full", () => {
    renderOverview("2026-03-31");
    const region = screen.getByRole("region", { name: "Limitations" });
    expect(within(region).queryByRole("button", { name: /^Show sources/ })).toBeNull();
    expect(
      within(region).getByText(/the nine modules delivered do not stand in for them\.$/),
    ).toBeVisible();
  });
});

describe("Overview, the first run on the issuer", () => {
  type FirstOverview = {
    metrics: unknown[];
    findings: unknown[];
    dates: unknown[];
    modules: { summary: string; items: { title: string; lead: string; state: string }[] };
    limitations: { count: string; items: unknown[] };
    sides: { columns: { items: unknown[] }[] };
  };
  const first = (): { head: { tabs: { modulesCount: string } }; overview: FirstOverview } =>
    (
      fixture.slice as {
        issuers: { id: string; runs: { id: string; head: never; overview: never }[] }[];
      }
    ).issuers
      .find((i) => i.id === "halden-aerostructures")
      ?.runs.find((r) => r.id === "2025-09-30") as never;

  it("draws every section with content under one h1", () => {
    renderOverview("2025-09-30");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(tiles().length).toBeGreaterThanOrEqual(3);
    const sides = within(screen.getByRole("region", { name: "For and against" })).getAllByRole(
      "heading",
      { level: 3 },
    );
    expect(sides.map((h) => h.textContent)).toEqual(["Supports the view", "Against the view"]);
    for (const side of sides) {
      expect(
        within(side.parentElement as HTMLElement).getAllByRole("listitem").length,
      ).toBeGreaterThanOrEqual(1);
    }
    for (const name of ["Key findings", "Dates to watch", "Modules", "Limitations"]) {
      const region = screen.getByRole("heading", { level: 2, name: new RegExp(`^${name}`) });
      expect(
        within(region.closest("section") as HTMLElement).getAllByRole("listitem").length,
      ).toBeGreaterThanOrEqual(1);
    }
  });

  it("agrees with itself: the module summary and the limitation count equal the listed items", () => {
    const { head, overview } = first();
    const [collapsed, ...rest] = overview.modules.items;
    const named = (collapsed?.lead ?? "").replace(/\.$/, "").split(/, (?=[A-Z])/).length;
    expect(collapsed?.title).toBe(`${String(named)} modules delivered`);
    const delivered = rest.filter((m) => m.state.startsWith("Delivered")).length;
    expect(rest).toHaveLength(delivered);
    expect(overview.modules.summary).toBe(
      `${String(named + delivered)} of ${head.tabs.modulesCount} delivered`,
    );
    expect(overview.limitations.count).toBe(String(overview.limitations.items.length));
    renderOverview("2025-09-30");
    expect(screen.getByText(overview.modules.summary)).toBeVisible();
    const region = screen.getByRole("region", { name: "Limitations" });
    expect(within(region).getByRole("heading", { level: 2 }).textContent).toBe(
      `Limitations${overview.limitations.count}`,
    );
    expect(within(region).getAllByRole("listitem")).toHaveLength(overview.limitations.items.length);
  });
});

describe("Overview, another run", () => {
  it("sweep SW-05: draws the limitations open again when the run changes under the page", () => {
    const view = renderOverview("2026-09-30");
    const region = screen.getByRole("region", { name: "Limitations" });
    fireEvent.click(within(region).getByRole("button", { name: "Collapse limitations" }));
    expect(within(region).queryByRole("listitem")).toBeNull();
    const route = routes.find((r) => r.path === PATH);
    if (route === undefined) throw new Error("no overview route");
    const data: LibraryData = {
      schema: "credit-os-data/1",
      issuers: fixture.issuers,
      library: fixture.slice,
    };
    view.rerender(
      <SourceContext.Provider value={data}>
        {route.render({ issuer: "halden-aerostructures", run: "2026-03-31" })}
      </SourceContext.Provider>,
    );
    const next = screen.getByRole("region", { name: "Limitations" });
    expect(within(next).getByRole("button", { name: "Collapse limitations" })).toBeVisible();
    expect(within(next).getAllByRole("listitem").length).toBeGreaterThan(0);
  });
});
