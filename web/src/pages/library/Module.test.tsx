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

const PATH = "/library/:issuer/:run/modules/:module";
const INDEX = "/library/:issuer/:run/modules";
const BASE = "#/library/halden-aerostructures/";

function renderRoute(
  pattern: string,
  params: Record<string, string>,
  library: unknown = fixture.slice,
) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === pattern);
  if (route === undefined) throw new Error(`no route ${pattern}`);
  return render(
    <SourceContext.Provider value={data}>{route.render(params)}</SourceContext.Provider>,
  );
}

const renderModule = (module: string, run = "2026-09-30", library: unknown = fixture.slice) =>
  renderRoute(PATH, { issuer: "halden-aerostructures", run, module }, library);

const nav = () => screen.getByRole("navigation", { name: "Modules and sections" });
const region = (name: string) => screen.getByRole("region", { name });
const sourceButtons = () => screen.queryAllByRole("button", { name: /^Show sources for/ });

describe("the module routes", () => {
  it("are titled Modules and the fixture visits each state", () => {
    expect(routes.find((r) => r.path === PATH)?.title).toBe("Modules");
    expect(routes.find((r) => r.path === INDEX)?.title).toBe("Modules");
    expect(routes.filter((r) => [PATH, INDEX].includes(r.path)).map((r) => r.layout)).toEqual([
      "bleed",
      "bleed",
    ]);
    expect(fixture.params[PATH]?.map((p) => [p["run"], p["module"]])).toEqual([
      ["2026-09-30", "business-profile"],
      ["2026-09-30", "capital-structure"],
      ["2026-09-30", "recovery"],
      ["2026-03-31", "forecast"],
      ["2026-06-30", "capital-structure"],
      ["2026-09-30", "no-such-module"],
    ]);
    expect(fixture.params[INDEX]?.map((p) => p["run"])).toEqual(["2026-09-30", "2026-06-30"]);
  });
});

describe("Module, a delivered prose module", () => {
  it("draws the issuer as the one h1, the module name as an h2 with its state badge, sections as h3", () => {
    renderModule("business-profile");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const name = screen.getByRole("heading", { level: 2, name: "Business profile" });
    expect(name.parentElement).toHaveTextContent(/^Business profileDelivered$/);
    expect(screen.getAllByRole("heading").map((h) => [h.tagName, h.textContent])).toEqual([
      ["H1", "Halden Aerostructures"],
      ["H2", "Business profile"],
      [
        "H3",
        "A sole-source aftermarket franchise carries a thinner, more cyclical original-equipment business.",
      ],
      ["H3", "Key findings"],
      ["H3", "Contrary evidence"],
      ["H3", "What would change the view"],
      ["H3", "Risks by probability and impact"],
      ["H3", "Indicators to watch"],
      ["H3", "Questions this module set out to answer"],
      ["H3", "Limitations2"],
    ]);
  });

  it("draws the bottom line band and the four findings with the mock's words", () => {
    renderModule("business-profile");
    const band = region("Bottom line");
    expect(within(band).getByText("Bottom line")).toBeVisible();
    expect(within(band).getByText(/^The aftermarket earns most of the profit/)).toBeVisible();
    expect(
      within(region("Key findings"))
        .getAllByRole("listitem")
        .map((i) => i.textContent),
    ).toEqual([
      "01The aftermarket is the franchiseParts and repair bring 44% of revenue and about three fifths of gross profit. Most parts are sole-source and certified to the airframe.",
      "02Original equipment is thin and fixed-priceNew-build contracts run five to seven years at fixed prices. Margin here is below every listed peer.",
      "03Concentration is the main exposureThree customers bring 58% of revenue and one engine programme 34%. Its ramp has slipped twice.",
      "04Purchases have added breadth, not scaleFour small purchases since 2023 added product lines. None changed the competitive position.",
    ]);
  });

  it("draws the contrary evidence as a warning that cannot be dismissed", () => {
    renderModule("business-profile");
    const alert = within(region("Contrary evidence")).getByRole("alert");
    expect(
      within(alert).getByText("Two airlines have begun certifying alternative parts"),
    ).toBeVisible();
    expect(alert).toHaveTextContent(/Management says none has passed certification/);
    expect(within(alert).queryByRole("button")).toBeNull();
  });

  it("sets the contrary evidence in the mock's 16/26 body with a 600 lead (x.css .s-alert)", () => {
    renderModule("business-profile");
    const host = within(region("Contrary evidence")).getByRole("alert")
      .parentElement as HTMLElement;
    expect(host).toHaveClass(
      "[&_p]:text-body",
      "[&_p]:max-w-[72ch]",
      "[&_strong]:text-body",
      "[&_strong]:font-semibold",
    );
  });

  it("draws what would change the view as the info note", () => {
    renderModule("business-profile");
    const note = within(region("What would change the view")).getByRole("note");
    expect(within(note).getByText("Loss of sole-source status on a top-ten part")).toBeVisible();
    expect(note).toHaveTextContent(/third slip in the engine programme’s ramp/);
  });

  it("draws the limitations with the module's gaps link, a count and a trace control for each traced item only", () => {
    renderModule("business-profile");
    const limits = region("Limitations");
    expect(within(limits).getByRole("heading", { level: 3 }).textContent).toBe("Limitations2");
    expect(
      within(limits).getByRole("link", { name: "See this module’s gaps in Evidence" }),
    ).toHaveAttribute("href", `${BASE}2026-09-30/evidence/gaps`);
    expect(within(limits).getAllByRole("listitem")).toHaveLength(2);
  });

  it("draws no records heading for a module with none, and no placeholder for one", () => {
    const { container } = renderModule("capital-structure");
    expect(screen.queryByText(/records/i)).toBeNull();
    expect(container.textContent).not.toMatch(/coming soon|placeholder|no records/i);
  });

  it("draws the trace controls the mock shows, each named as the mock names it, and opens a drawer", () => {
    renderModule("business-profile");
    expect(sourceButtons().map((b) => b.getAttribute("aria-label"))).toEqual([
      "Show sources for the bottom line",
      "Show sources for this finding",
      "Show sources for this finding",
      "Show sources for this finding",
      "Show sources for this finding",
      "Show sources for the contrary evidence",
      "Show sources for the trigger",
      "Show sources for the risk matrix",
      ...Array<string>(5).fill("Show sources for this risk"),
      ...Array<string>(4).fill("Show sources for this indicator"),
      ...Array<string>(2).fill("Show sources for this answer"),
      "Show sources for this limitation",
      "Show sources for this limitation",
    ]);
    fireEvent.click(sourceButtons()[1] as HTMLElement);
    expect(screen.getByRole("dialog", { name: "Sources for aftermarket share" })).toBeVisible();
  });

  it("turns every control on with Show sources, as the mock draws this page", () => {
    const { container } = renderModule("business-profile");
    fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "on");
    expect(sourceButtons()).toHaveLength(21);
  });

  it("opens the drawer of each passage's own module-level trace", () => {
    renderModule("business-profile");
    const titles = [];
    for (const button of sourceButtons()) {
      fireEvent.click(button);
      titles.push(screen.getByRole("dialog").getAttribute("aria-label"));
      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    }
    expect(new Set(titles).size).toBe(21);
  });

  it("shows no audit material and no module or trace code", () => {
    const { container } = renderModule("business-profile");
    const all = [container.innerHTML, container.textContent].join(" ");
    expect(all).not.toMatch(/T-\d{4}|C-\d{4}|\.pdf|hash|aftermarket-share|engine-programme|bp-/i);
  });
});

describe("Module, the risk matrix", () => {
  const card = () => region("Table side of the risk matrix");

  it("draws the Table side only, under the block's title, with no Chart or Table toggle", () => {
    renderModule("business-profile");
    expect(
      within(card()).getByRole("heading", { level: 3, name: "Risks by probability and impact" }),
    ).toBeVisible();
    expect(screen.queryByRole("radio", { name: /chart|table/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Chart|Table)$/ })).toBeNull();
  });

  it("draws the mock's five risks with their grades and n.a. for the missing one", () => {
    renderModule("business-profile");
    const table = within(card()).getByRole("table", { name: "Risks by probability and impact" });
    const rows = within(table).getAllByRole("row");
    expect(
      within(rows[0] as HTMLElement)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Risk", "Probability", "Impact", "Sources"]);
    const text = (row: HTMLElement) =>
      [within(row).getByRole("rowheader"), ...within(row).getAllByRole("cell")]
        .slice(0, 3)
        .map((c) => c.textContent);
    expect(rows.slice(1).map((r) => text(r))).toEqual([
      ["Engine programme delay", "Medium", "High"],
      ["Loss of sole-source status", "Low", "High"],
      ["Customer concentration", "Medium", "Medium"],
      ["Input cost inflation", "High", "Low"],
      ["Tariff exposure", "n.a.not available", "Medium"],
    ]);
    const tariff = within(rows[5] as HTMLElement).getAllByRole("cell")[0] as HTMLElement;
    expect(tariff.querySelector("[aria-hidden=true]")).toHaveTextContent("n.a.");
    expect(within(card()).queryByText("0")).toBeNull();
  });

  it("draws one trace control for the block and one for each risk row", () => {
    renderModule("business-profile");
    expect(
      within(card())
        .getAllByRole("button")
        .map((b) => b.getAttribute("aria-label")),
    ).toEqual([
      "Show sources for the risk matrix",
      ...Array<string>(5).fill("Show sources for this risk"),
    ]);
    fireEvent.click(within(card()).getAllByRole("button")[0] as HTMLElement);
    expect(screen.getByRole("dialog", { name: "Sources for the risk matrix" })).toBeVisible();
  });

  it("is one Records entry in the navigator, and moves focus to the first block's heading", () => {
    renderModule("business-profile");
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    fireEvent.click(within(nav()).getByRole("button", { name: "Records" }));
    const heading = screen.getByRole("heading", { name: "Risks by probability and impact" });
    expect(scroll.mock.contexts[0]).toBe(heading.closest("[data-section]"));
    expect(heading).toHaveFocus();
    expect(heading).toHaveAttribute("tabindex", "-1");
    expect(heading).toHaveClass("focus-visible:ring-2", "focus-visible:ring-brand");
    Reflect.deleteProperty(Element.prototype, "scrollIntoView");
  });
});

describe("Module, the watch list", () => {
  const watch = () => region("Indicators to watch");
  const rows = () => within(watch()).getAllByRole("listitem").slice(0, 4);

  it("lists the mock's four indicators with their thresholds", () => {
    renderModule("business-profile");
    expect(
      within(watch())
        .getByRole("heading", { level: 3, name: "Indicators to watch" })
        .getAttribute("tabindex"),
    ).toBe("-1");
    expect(rows().map((r) => r.textContent)).toEqual([
      "Engine deliveries per monthBelow 40 for two quarters",
      "Aftermarket price rise at renewalBelow 3%",
      "Alternative parts certifiedAny top-ten part",
      "Aftermarket share of gross profitBelow 55%",
    ]);
  });

  it("marks each indicator Leading or Lagging with an icon named by the word", () => {
    renderModule("business-profile");
    expect(rows().map((r) => within(r).getByRole("img").getAttribute("aria-label"))).toEqual([
      "Leading",
      "Leading",
      "Leading",
      "Lagging",
    ]);
  });

  it("explains the two icons in a legend that the screen reader does not repeat", () => {
    renderModule("business-profile");
    const legend = within(watch()).getByText(/^LeadingLagging$/);
    expect(legend.querySelectorAll("[aria-hidden=true]")).toHaveLength(2);
    expect(within(watch()).getAllByRole("img")).toHaveLength(4);
  });

  it("draws one trace control for each indicator", () => {
    renderModule("business-profile");
    const buttons = within(watch()).getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual(
      Array<string>(4).fill("Show sources for this indicator"),
    );
    fireEvent.click(buttons[3] as HTMLElement);
    expect(
      screen.getByRole("dialog", { name: "Sources for the gross profit share" }),
    ).toBeVisible();
  });
});

describe("Module, the questions", () => {
  const questions = () => region("Questions this module set out to answer");
  const rows = () => Array.from(questions().querySelectorAll("details"));
  const BADGES = /^(Answered|Partly answered|Not answered)$/;

  it("draws the mock's three questions in order, then the added long one, each with its state", () => {
    renderModule("business-profile");
    expect(
      within(questions())
        .getAllByText(/\?$/)
        .map((q) => q.textContent),
    ).toEqual([
      "How durable is aftermarket pricing?",
      "How exposed is revenue to one programme?",
      "What share of contracts can pass through cost inflation?",
      "How much of the order book is firm?",
    ]);
    expect(
      within(questions())
        .getAllByText(BADGES)
        .map((b) => b.textContent),
    ).toEqual(["Answered", "Partly answered", "Not answered", "Answered"]);
  });

  it("opens the first answer as the mock draws it and words it as the mock does", () => {
    renderModule("business-profile");
    expect(rows()).toHaveLength(2);
    const first = rows()[0] as HTMLElement;
    expect(first).toHaveAttribute("open");
    expect(first).toHaveTextContent(
      "Durable for the parts where Halden is the only certified source, which carry about three fifths of gross profit. Price rises of 4 to 6% a year have held since 2021.",
    );
    expect(
      within(first).getByRole("button", { name: "Show sources for this answer" }),
    ).toBeVisible();
    expect(rows()[1]).not.toHaveAttribute("open");
  });

  it("draws a partly or not answered question as a plain row: no toggle that opens nothing", () => {
    renderModule("business-profile");
    for (const text of [
      "How exposed is revenue to one programme?",
      "What share of contracts can pass through cost inflation?",
    ]) {
      const row = within(questions()).getByText(text).closest("li") as HTMLElement;
      expect(row.querySelector("details, summary, button")).toBeNull();
      expect(within(row).getByText(BADGES)).toBeVisible();
    }
  });

  it("opens a closed answer and closes it again through its summary", () => {
    renderModule("business-profile");
    const closed = rows()[1] as HTMLElement;
    const summary = closed.querySelector("summary") as HTMLElement;
    expect(summary).not.toHaveAttribute("tabindex");
    fireEvent.click(summary);
    expect(closed).toHaveAttribute("open");
    fireEvent.click(summary);
    expect(closed).not.toHaveAttribute("open");
  });

  it("wraps a long answer in full at the reading width, with nothing cut", () => {
    renderModule("business-profile");
    const long = rows()[1] as HTMLElement;
    const answer = within(long).getByText(/^About four fifths of the order book/);
    expect(answer.textContent).toMatch(/which the files do not show\.$/);
    expect(answer.className).toMatch(/max-w-\[72ch\]/);
    expect(long.innerHTML).not.toMatch(/truncate|line-clamp|text-ellipsis/);
  });
});

describe("Module, the navigator", () => {
  it("is one navigation of two named groups, sticky from the wide layout and scrolling by itself", () => {
    renderModule("business-profile");
    expect(nav()).toHaveClass("min-[1001px]:sticky", "min-[1001px]:overflow-y-auto");
    expect(nav().className).toMatch(/max-h-\[calc\(100vh/);
    expect(nav().parentElement).toHaveClass("min-[1001px]:grid-cols-[240px_minmax(0,1fr)]");
    expect(within(nav()).getByText("On this page")).toBeVisible();
    expect(within(nav()).getByText("Modules in this run")).toBeVisible();
    expect(
      within(nav())
        .getAllByRole("list")
        .map((l) => l.getAttribute("aria-labelledby")),
    ).toEqual(
      within(nav())
        .getAllByText(/^(On this page|Modules in this run)$/)
        .map((t) => t.id),
    );
  });

  it("lists this module's sections, Records among them", () => {
    renderModule("business-profile");
    const sections = within(within(nav()).getAllByRole("list")[0] as HTMLElement).getAllByRole(
      "button",
    );
    expect(sections.map((s) => s.textContent)).toEqual([
      "Bottom line",
      "Key findings",
      "Contrary evidence",
      "What would change the view",
      "Records",
      "Limitations",
    ]);
  });

  it("gives each section entry the mock's 20px icon slot", () => {
    renderModule("business-profile");
    const entries = within(within(nav()).getAllByRole("list")[0] as HTMLElement).getAllByRole(
      "button",
    );
    for (const entry of entries) {
      const slot = entry.querySelector("svg") as SVGElement;
      expect(slot).toHaveAttribute("aria-hidden", "true");
      expect(slot).toHaveClass("size-5", "flex-none", "opacity-75");
    }
  });

  it("lists only the sections a module has", () => {
    renderModule("capital-structure");
    expect(
      within(within(nav()).getAllByRole("list")[0] as HTMLElement)
        .getAllByRole("button")
        .map((s) => s.textContent),
    ).toEqual(["Bottom line", "Key findings", "Limitations"]);
  });

  it("moves focus and scroll to the section without changing the address", () => {
    renderModule("business-profile");
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    window.location.hash = "#/library/halden-aerostructures/2026-09-30/modules/business-profile";
    const before = window.location.hash;
    fireEvent.click(within(nav()).getByRole("button", { name: "Contrary evidence" }));
    const target = screen.getByRole("heading", { level: 3, name: "Contrary evidence" });
    expect(scroll).toHaveBeenCalledTimes(1);
    expect(scroll.mock.contexts[0]).toBe(target.closest("[data-section]"));
    expect(target).toHaveFocus();
    expect(target).toHaveAttribute("tabindex", "-1");
    expect(target).toHaveClass("focus-visible:ring-2", "focus-visible:ring-brand");
    expect(window.location.hash).toBe(before);
    expect(within(nav()).getByRole("button", { name: "Contrary evidence" })).toHaveAttribute(
      "aria-current",
      "location",
    );
    expect(within(nav()).getByRole("button", { name: "Bottom line" })).not.toHaveAttribute(
      "aria-current",
    );
    window.location.hash = "";
    Reflect.deleteProperty(Element.prototype, "scrollIntoView");
  });

  it("lists all thirteen modules with the state in each name and the current one marked", () => {
    renderModule("business-profile");
    const links = within(nav()).getAllByRole("link");
    expect(links).toHaveLength(13);
    expect(links[0]).toHaveAccessibleName("Business profile, Delivered");
    const named = links[0]?.querySelector(".sr-only")?.parentElement as HTMLElement;
    expect(named).not.toBe(links[0]);
    expect(named.textContent).toBe("Business profile, Delivered");
    expect(links[0]).toHaveAttribute("aria-current", "page");
    expect(links[0]).toHaveAttribute("href", `${BASE}2026-09-30/modules/business-profile`);
    expect(links.filter((l) => l.hasAttribute("aria-current"))).toHaveLength(1);
    expect(
      within(nav()).getByRole("link", { name: "Capital structure, Delivered with gaps" }),
    ).toBeVisible();
    expect(
      within(nav()).getByRole("link", { name: "Peer comparison, Delivered with gaps" }),
    ).toBeVisible();
    expect(within(nav()).getByRole("link", { name: "Recovery, Not assessable" })).toBeVisible();
    expect(links.map((l) => l.querySelector("svg")?.getAttribute("data-shape"))).toEqual([
      "filled circle",
      "filled circle",
      "filled circle",
      "filled circle",
      "dashed ring",
      "filled circle",
      "filled circle",
      "dashed ring",
      "slashed circle",
      "filled circle",
      "filled circle",
      "filled circle",
      "filled circle",
    ]);
  });
});

describe("Module, delivered with gaps", () => {
  it("draws the state badge beside the name and the prose passages only", () => {
    renderModule("capital-structure");
    const name = screen.getByRole("heading", { level: 2, name: "Capital structure" });
    expect(name.parentElement).toHaveTextContent("Capital structureDelivered with gaps");
    expect(
      within(region("Key findings"))
        .getAllByRole("listitem")
        .map((i) => i.textContent.slice(0, 40)),
    ).toEqual([
      "01The first maturity is the weakest clai",
      "02The covenant is a formalityIt tests on",
      "03Capacity for more debt remainsBaskets ",
    ]);
    expect(screen.queryByRole("region", { name: "Contrary evidence" })).toBeNull();
    expect(screen.queryByRole("region", { name: "What would change the view" })).toBeNull();
    expect(within(region("Limitations")).getAllByRole("listitem")).toHaveLength(3);
    expect(sourceButtons()).toHaveLength(2);
  });
});

describe("Module, a module that could not be delivered", () => {
  it("draws the name, the kit's blocked line, the note and the gap link, and nothing else", () => {
    renderModule("recovery");
    expect(screen.getByRole("heading", { level: 2, name: "Recovery" })).toBeVisible();
    expect(screen.getByText("Not assessable")).toBeVisible();
    expect(
      screen.getByText(
        "The security package documents were not among the files provided, so recovery by class could not be assessed.",
      ),
    ).toBeVisible();
    expect(
      screen.getByText(/^Nothing from this module is shown and no figure elsewhere rests on it/),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "See this gap in Evidence" })).toHaveAttribute(
      "href",
      `${BASE}2026-09-30/evidence/gaps`,
    );
    expect(screen.queryByRole("region", { name: "Bottom line" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Limitations" })).toBeNull();
    expect(within(nav()).queryByText("On this page")).toBeNull();
    expect(within(nav()).getByText("Modules in this run")).toBeVisible();
    expect(screen.getAllByRole("heading").map((h) => h.tagName)).toEqual(["H1", "H2"]);
  });

  it("draws a module that did not run as Not run, never as Not assessable", () => {
    renderModule("forecast", "2026-03-31");
    expect(screen.getByRole("heading", { level: 2, name: "Forecast" })).toBeVisible();
    expect(
      screen.getByText("The run reached its cost cap before this module started."),
    ).toBeVisible();
    expect(screen.getAllByText("Not run").length).toBeGreaterThan(0);
    expect(screen.queryByText("Not assessable")).toBeNull();
    const links = within(nav()).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual([
      "Business profile, Delivered",
      "Industry and competition, Delivered",
      "Financial performance, Not run",
      "Cash flow and liquidity, Not run",
      "Capital structure, Delivered with gaps",
      "Covenants and documentation, Delivered",
      "Management and governance, Delivered",
      "Peer comparison, Delivered with gaps",
      "Recovery, Not run",
      "Rating outlook, Delivered",
      "Environmental, social and governance, Delivered",
      "Forecast, Not run",
      "Credit snapshot, Delivered",
    ]);
    expect(links.filter((l) => l.hasAttribute("aria-current")).map((l) => l.textContent)).toEqual([
      "Forecast, Not run",
    ]);
  });
});

describe("Module, a limitation longer than three lines", () => {
  const layout = (overflows: boolean) => {
    vi.spyOn(Element.prototype, "scrollHeight", "get").mockReturnValue(overflows ? 90 : 60);
    vi.spyOn(Element.prototype, "clientHeight", "get").mockReturnValue(60);
  };
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("clamps at three lines and offers Show all, then Show less, and prints open", () => {
    layout(true);
    renderModule("business-profile");
    const limits = region("Limitations");
    const buttons = within(limits).getAllByRole("button", { name: /^Show (all|less)$/ });
    expect(buttons).toHaveLength(2);
    const long = within(limits).getByText(/^The share of revenue under cost pass-through/);
    expect(long).toHaveClass("line-clamp-3", "print:line-clamp-none");
    const show = buttons[1] as HTMLElement;
    expect(show).toHaveAttribute("aria-expanded", "false");
    expect(show).toHaveClass("print:hidden");
    fireEvent.click(show);
    expect(long).not.toHaveClass("line-clamp-3");
    expect(show).toHaveTextContent("Show less");
    expect(show).toHaveAttribute("aria-expanded", "true");
    expect(long.textContent).toMatch(/which the files do not show\.$/);
    fireEvent.click(show);
    expect(long).toHaveClass("line-clamp-3");
    expect(show).toHaveTextContent("Show all");
  });

  it("builds one observer for each limitation, not one for every render", () => {
    layout(true);
    const Original = globalThis.ResizeObserver;
    let built = 0;
    globalThis.ResizeObserver = class extends Original {
      constructor(callback: ResizeObserverCallback) {
        super(callback);
        built += 1;
      }
    };
    try {
      renderModule("business-profile");
      const first = built;
      expect(first).toBe(2);
      fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
      fireEvent.click(screen.getByRole("switch", { name: "Show sources" }));
      expect(built).toBe(first);
    } finally {
      globalThis.ResizeObserver = Original;
    }
  });

  it("offers nothing when the text fits in three lines", () => {
    layout(false);
    renderModule("business-profile");
    expect(
      within(region("Limitations")).queryByRole("button", { name: /^Show (all|less)$/ }),
    ).toBeNull();
  });
});

describe("Module, states of the address", () => {
  it("says which module is missing, with the way back, under the issuer's one h1", () => {
    const { container } = renderModule("no-such-module");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "No such module" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toBeVisible();
    expect(container.textContent).not.toMatch(/Page not found|could not be read/);
  });

  it("says no such run and no such issuer by the page's own name", () => {
    renderModule("recovery", "1999-01-01");
    expect(screen.getByRole("heading", { level: 1, name: "Modules" })).toBeVisible();
    expect(screen.getByText("No such run")).toBeVisible();
    cleanup();
    renderRoute(PATH, { issuer: "nobody", run: "2026-09-30", module: "recovery" });
    expect(screen.getByText("No such issuer")).toBeVisible();
  });

  it("draws a loading run as the skeleton only", () => {
    const { container } = renderModule("capital-structure", "2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("navigation", { name: "Modules and sections" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

describe("Module, the index route", () => {
  const index = (run: string, library: unknown = fixture.slice) =>
    renderRoute(INDEX, { issuer: "halden-aerostructures", run }, library);

  it("draws the run's first module, the first of its list", () => {
    index("2026-09-30");
    expect(screen.getByRole("heading", { level: 2, name: "Business profile" })).toBeVisible();
    const links = within(nav()).getAllByRole("link");
    expect(links[0]).toHaveAttribute("aria-current", "page");
    expect(links.filter((l) => l.hasAttribute("aria-current"))).toHaveLength(1);
  });

  it("opens the first module on the capped and the first run too", () => {
    for (const run of ["2026-03-31", "2025-09-30"]) {
      index(run);
      expect(screen.getByRole("heading", { level: 2, name: "Business profile" })).toBeVisible();
      expect(within(nav()).getAllByRole("link")).toHaveLength(13);
      cleanup();
    }
  });

  it("draws a loading run as the skeleton", () => {
    const { container } = index("2026-06-30");
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
  });

  it("says the run has no modules when it holds none", () => {
    const slice = structuredClone(fixture.slice) as {
      issuers: { runs: { modules: unknown[]; head: Json; overview: Json; changes: Json }[] }[];
    };
    const run = slice.issuers[0]?.runs[3] as { modules: unknown[]; head: Json; overview: Json };
    run.modules = [];
    run.head["firstModule"] = null;
    (run.overview["modules"] as { items: Json[] }).items = [
      { title: "Nothing", lead: "No module ran.", state: "Not run", module: null },
    ];
    index("2025-09-30", slice);
    expect(screen.getByRole("heading", { level: 2, name: "No modules in this run" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Back to the library" })).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
