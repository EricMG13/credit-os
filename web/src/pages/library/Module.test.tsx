import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, renderHook, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { useSourcesOn } from "./parts/SourcesSwitch";
import { moduleViewKey } from "./Module";
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

/** Show sources is kept for the session, so each test starts with it off. */
afterEach(() => {
  renderHook(() => useSourcesOn()).result.current[1](false);
});

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
      ["H3", "How a programme delay reaches the credit"],
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
    const { container } = renderModule("covenants-and-documentation");
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
  }, 20_000);

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
  const rows = () => within(watch()).getAllByRole("listitem");

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

describe("Module, the pathway", () => {
  const pathway = () => region("How a programme delay reaches the credit");

  it("draws the mock's four steps in order as an ordered list, each with its title and line", () => {
    renderModule("business-profile");
    const steps = within(within(pathway()).getByRole("list")).getAllByRole("listitem");
    expect(within(pathway()).getByRole("list").tagName).toBe("OL");
    expect(steps.map((i) => i.textContent)).toEqual([
      "Ramp slipsDeliveries fall short of plan",
      "Inventory staysCash tied up for longer",
      "Cash flow fallsLess debt repaid from operations",
      "Leverage holdsRefinancing on weaker terms",
    ]);
  });

  it("numbers the steps by the list and not by a figure the page makes", () => {
    renderModule("business-profile");
    const first = within(pathway()).getAllByRole("listitem")[0] as HTMLElement;
    const ring = first.querySelector("[aria-hidden=true]") as HTMLElement;
    expect(ring.textContent).toBe("");
    expect(ring.className).toMatch(/content-\[counter\(step\)\]/);
  });

  it("sets the steps in one row from 901px wide and stacks them below, with no trace control", () => {
    renderModule("business-profile");
    expect(within(pathway()).getByRole("list")).toHaveClass(
      "grid-cols-1",
      "min-[901px]:grid-flow-col",
    );
    expect(within(pathway()).queryByRole("button")).toBeNull();
  });

  it("sets the number ring and the line in the mock's 13px caption size", () => {
    renderModule("business-profile");
    const first = within(pathway()).getAllByRole("listitem")[0] as HTMLElement;
    expect(first.querySelector("[aria-hidden=true]")).toHaveClass("text-caption");
    expect(first.querySelector("small")).toHaveClass("text-caption");
  });
});

describe("Module, records that sit side by side", () => {
  it("stack up to 1199px wide and go two-up from 1200px, like the chart pair", () => {
    renderModule("business-profile");
    const row = region("Indicators to watch").parentElement as HTMLElement;
    expect(row).toHaveClass("grid-cols-1", "min-[1200px]:grid-cols-2");
    expect(row).not.toHaveClass("md:grid-cols-2", "min-[1001px]:grid-cols-2");
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
    renderModule("covenants-and-documentation");
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

  it("forgets the selected section when the run changes to one whose same module lacks it", () => {
    Element.prototype.scrollIntoView = vi.fn();
    const data: LibraryData = {
      schema: "credit-os-data/1",
      issuers: fixture.issuers,
      library: fixture.slice,
    };
    const route = routes.find((r) => r.path === PATH);
    if (route === undefined) throw new Error(`no route ${PATH}`);
    const at = (run: string) => (
      <SourceContext.Provider value={data}>
        {route.render({ issuer: "halden-aerostructures", run, module: "business-profile" })}
      </SourceContext.Provider>
    );
    const view = render(at("2026-09-30"));
    fireEvent.click(within(nav()).getByRole("button", { name: "Contrary evidence" }));
    expect(within(nav()).getByRole("button", { name: "Contrary evidence" })).toHaveAttribute(
      "aria-current",
      "location",
    );
    view.rerender(at("2026-03-31"));
    expect(within(nav()).queryByRole("button", { name: "Contrary evidence" })).toBeNull();
    const current = within(nav())
      .getAllByRole("button")
      .filter((b) => b.getAttribute("aria-current") === "location");
    expect(current.map((b) => b.textContent)).toEqual(["Bottom line"]);
    Reflect.deleteProperty(Element.prototype, "scrollIntoView");
  });

  it("forgets the selected section when the issuer changes and run and module stay", () => {
    Element.prototype.scrollIntoView = vi.fn();
    const slice = structuredClone(fixture.slice) as {
      issuers: { id: string; name: string; runs: { id: string; modules: unknown }[] }[];
    };
    const [first] = slice.issuers;
    if (first === undefined) throw new Error("no issuer");
    const earlier = first.runs.find((r) => r.id === "2026-03-31");
    if (earlier === undefined) throw new Error("no earlier run");
    // The same run id and module under another issuer, whose copy of the run lacks the section:
    // the earlier run, filed under the later run's id.
    const other = structuredClone(first);
    const slot = other.runs.findIndex((r) => r.id === "2026-09-30");
    if (slot === -1) throw new Error("no run");
    other.runs[slot] = { ...structuredClone(earlier), id: "2026-09-30" };
    other.id = "halden-copy";
    other.name = "Halden copy";
    slice.issuers.push(other);
    const data: LibraryData = {
      schema: "credit-os-data/1",
      issuers: fixture.issuers,
      library: slice,
    };
    const route = routes.find((r) => r.path === PATH);
    if (route === undefined) throw new Error(`no route ${PATH}`);
    const at = (issuer: string) => (
      <SourceContext.Provider value={data}>
        {route.render({ issuer, run: "2026-09-30", module: "business-profile" })}
      </SourceContext.Provider>
    );
    const view = render(at("halden-aerostructures"));
    fireEvent.click(within(nav()).getByRole("button", { name: "Contrary evidence" }));
    expect(within(nav()).getByRole("button", { name: "Contrary evidence" })).toHaveAttribute(
      "aria-current",
      "location",
    );
    view.rerender(at("halden-copy"));
    expect(within(nav()).queryByRole("button", { name: "Contrary evidence" })).toBeNull();
    const current = within(nav())
      .getAllByRole("button")
      .filter((b) => b.getAttribute("aria-current") === "location");
    expect(current.map((b) => b.textContent)).toEqual(["Bottom line"]);
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
  it("draws the state badge beside the name, the prose passages, and the limitations", () => {
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
  });
});

/** A copy of the slice with the data module's records edited by `edit`. */
function withRecords(edit: (records: Json[]) => void): Json {
  const slice = structuredClone(fixture.slice) as { issuers: { runs: { modules: Json[] }[] }[] };
  const module = slice.issuers[0]?.runs[0]?.modules.find((m) => m["id"] === "capital-structure");
  edit((module?.["body"] as { records: Json[] }).records);
  return slice;
}
const blockOf = (records: Json[], kind: string) =>
  records.find((r) => r["kind"] === kind) as { items: Json[] } & Json;

describe("Module, the headline figures", () => {
  const figures = () => region("Headline figures");

  it("draws the mock's six figures with their notes in its order, three across from 640px", () => {
    renderModule("capital-structure");
    const tiles = within(figures()).getAllByRole("listitem");
    expect(tiles.map((t) => t.textContent)).toEqual([
      "Gross debtUSD 2,398mAt 30 Sep 2026",
      "Net debtUSD 2,236mAfter USD 162m cash",
      "Net leverage4.6xNet debt to EBITDA",
      "Secured leverage3.3xFirst-lien net debt to EBITDA",
      "Average cost of debtWithheldMarked confidential in the source",
      "Next maturityMar 2028USD 310m unsecured notes",
    ]);
    expect(tiles[0]?.parentElement).toHaveClass("grid-cols-1", "sm:grid-cols-3");
  });

  it("draws the withheld figure as the kit's Withheld, never as a number or n.a.", () => {
    renderModule("capital-structure");
    const tile = within(figures()).getAllByRole("listitem")[4] as HTMLElement;
    expect(within(tile).getByText("Withheld")).toBeVisible();
    expect(tile).not.toHaveTextContent(/n\.a\.|\d/);
  });

  it("names the block by a heading only a screen reader meets, which the navigator focuses", () => {
    renderModule("capital-structure");
    const heading = screen.getByRole("heading", { level: 3, name: "Headline figures" });
    expect(heading).toHaveClass("sr-only");
    expect(figures()).toHaveClass(
      "has-[>[tabindex='-1']:focus-visible]:ring-2",
      "has-[>[tabindex='-1']:focus-visible]:ring-brand",
    );
    expect(figures()).not.toHaveClass("has-[:focus-visible]:ring-2");
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    fireEvent.click(within(nav()).getByRole("button", { name: "Headline figures" }));
    expect(heading).toHaveFocus();
    expect(scroll.mock.contexts[0]).toBe(heading.closest("[data-section]"));
    Reflect.deleteProperty(Element.prototype, "scrollIntoView");
  });

  it("draws one trace control for each figure, the withheld one included, each with its own drawer", () => {
    renderModule("capital-structure");
    const buttons = within(figures()).getAllByRole("button", {
      name: "Show sources for this figure",
    });
    expect(buttons).toHaveLength(6);
    fireEvent.click(buttons[0] as HTMLElement);
    expect(screen.getByRole("dialog", { name: "Sources for gross debt" })).toBeVisible();
  });

  it("draws zero as zero beside n.a., and a gap as the kit's panel", () => {
    const library = withRecords((records) => {
      const items = blockOf(records, "metrics").items;
      (items[0] as Json)["value"] = { kind: "value", text: "USD 0m", at: 0 };
      (items[1] as Json)["value"] = null;
      (items[2] as Json)["value"] = { kind: "gap", reason: "The debt schedule was not provided." };
    });
    renderModule("capital-structure", "2026-09-30", library);
    const tiles = within(figures()).getAllByRole("listitem");
    expect(tiles[0]).toHaveTextContent("USD 0m");
    expect(tiles[1]).toHaveTextContent("n.a.not available");
    expect(tiles[1]).not.toHaveTextContent("0");
    expect(within(tiles[2] as HTMLElement).getByText("Not established for this run")).toBeVisible();
  });
});

describe("Module, the measures and their consequence", () => {
  const measures = () => region("Measures and their consequence");

  it("draws the mock's three measures: figure, change line and consequence", () => {
    renderModule("capital-structure");
    const stats = within(measures()).getAllByRole("listitem");
    expect(stats.map((t) => t.textContent)).toEqual([
      "Net leverage4.6xLower by 0.3x on 2025Back inside the range both agencies set for the current rating.",
      "LiquidityUSD 412mLower by USD 43m on JuneCovers every maturity before March 2028 more than four times.",
      "Interest cover2.4xEarlier period n.a.not availableThin: a one-point rise in floating rates would take it close to 2.0x.",
    ]);
    expect(stats[0]?.parentElement).toHaveClass("grid-cols-1", "sm:grid-cols-3", "gap-10");
  });

  it("marks the delivered direction, and draws no mark for a missing earlier period", () => {
    renderModule("capital-structure");
    const stats = within(measures()).getAllByRole("listitem");
    expect(stats[0]?.querySelector("[data-direction]")).toHaveAttribute("data-direction", "down");
    expect(stats[1]?.querySelector("[data-direction]")).toHaveAttribute("data-direction", "down");
    expect(stats[2]?.querySelector("[data-direction]")).toBeNull();
    expect(stats[2]?.querySelector("[aria-hidden=true]")).toHaveTextContent("n.a.");
  });

  it("draws one trace control for each measure, named as the mock names it", () => {
    renderModule("capital-structure");
    const buttons = within(measures()).getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual(
      Array<string>(3).fill("Show sources for this measure"),
    );
    fireEvent.click(buttons[2] as HTMLElement);
    expect(
      screen.getByRole("dialog", { name: "Sources for interest cover in this module" }),
    ).toBeVisible();
  });

  it("draws a missing earlier period beside no change, and a flat mark as delivered", () => {
    const library = withRecords((records) => {
      const items = blockOf(records, "measures").items;
      (items[1] as Json)["earlier"] = null;
      (items[1] as Json)["delta"] = null;
      (items[2] as Json)["earlier"] = { kind: "value", text: "2.4x", at: 2.4 };
      (items[2] as Json)["delta"] = { text: "Unchanged on 2025", direction: "flat" };
    });
    renderModule("capital-structure", "2026-09-30", library);
    const stats = within(measures()).getAllByRole("listitem");
    expect(stats[1]).toHaveTextContent("Earlier period n.a.");
    expect(stats[1]?.querySelector("[data-direction]")).toBeNull();
    expect(stats[2]?.querySelector("[data-direction]")).toHaveAttribute("data-direction", "flat");
  });
});

describe("Module, the facility terms", () => {
  const terms = () => region("Facility terms");
  const facts = () => terms().querySelectorAll("dl > div");

  it("draws the groups with their names and each row as a term and its value", () => {
    renderModule("capital-structure");
    expect(within(terms()).getAllByRole("heading")).toHaveLength(1);
    expect(
      within(terms())
        .getAllByRole("term")
        .map((t) => t.textContent),
    ).toEqual(["Amount", "Margin", "Maturity", "Size", "Drawn", "Commitment fee", "Availability"]);
    expect([...facts()].map((f) => f.textContent)).toEqual([
      "AmountUSD 1,150m",
      "MarginReference rate plus 3.25%",
      "MaturitySeptember 2030",
      "SizeUSD 250m",
      "DrawnUSD 0m",
      "Commitment feen.a.not available",
      "AvailabilityWithheld",
    ]);
    expect(
      [...terms().querySelectorAll("dl")].map((dl) => dl.getAttribute("aria-labelledby")),
    ).toEqual(
      ["Term loan B", "Revolving facility", "Receivables facility"].map(
        (name) => within(terms()).getByText(name).id,
      ),
    );
  });

  it("keeps zero as zero beside n.a., and draws a withheld value as the kit's Withheld", () => {
    renderModule("capital-structure");
    const [, , , , drawn, fee, receivables] = [...facts()] as HTMLElement[];
    expect(drawn).toHaveTextContent("USD 0m");
    expect(fee).not.toHaveTextContent("0");
    expect(within(receivables as HTMLElement).getByText("Withheld")).toBeVisible();
  });

  it("draws one trace control for each row, named as the mock names it", () => {
    renderModule("capital-structure");
    const buttons = within(terms()).getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual(
      Array<string>(7).fill("Show sources for this fact"),
    );
    fireEvent.click(buttons[0] as HTMLElement);
    expect(screen.getByRole("dialog", { name: "Sources for the term loan" })).toBeVisible();
  });

  it("sets a group of no name without a label, and a gap as the inline badge", () => {
    const library = withRecords((records) => {
      const groups = (records.find((r) => r["kind"] === "facts") as Json)["groups"] as Json[];
      (groups[0] as Json)["name"] = null;
      ((groups[0]?.["rows"] as Json[])[0] as Json)["value"] = { kind: "gap", reason: "Not read." };
    });
    renderModule("capital-structure", "2026-09-30", library);
    expect(within(terms()).queryByText("Term loan B")).toBeNull();
    expect(terms().querySelector("dl")).not.toHaveAttribute("aria-labelledby");
    expect(within(terms()).getByText("Not established for this run")).toBeVisible();
  });
});

describe("Module, the documentation tests", () => {
  const tests = () => region("Documentation tests");
  const groups = () => within(tests()).getAllByRole("group");

  it("draws the not met group first, as delivered, then the met group, each with its count", () => {
    renderModule("capital-structure");
    expect(groups().map((g) => g.firstElementChild?.textContent)).toEqual(["Not met1", "Met3"]);
    expect(
      groups().map((g) =>
        within(g)
          .getAllByRole("listitem")
          .map((i) => i.textContent),
      ),
    ).toEqual([
      ["Compliance certificate on timeDelivered 12 days late"],
      [
        "First-lien net leverage3.3x against 6.5x",
        "Restricted payments basketUSD 20m of USD 75m used",
        "Receivables facility availabilityWithheld",
      ],
    ]);
  });

  it("names each group by its status word and shape, never by colour alone", () => {
    renderModule("capital-structure");
    const [notMet, met] = groups();
    expect(notMet?.querySelector("svg")).toHaveAttribute("data-shape", "triangle");
    expect(met?.querySelector("svg")).toHaveAttribute("data-shape", "filled circle");
    expect(groups().map((g) => g.getAttribute("aria-labelledby"))).toEqual(
      groups().map((g) => g.firstElementChild?.id),
    );
  });

  it("draws the withheld test as the kit's Withheld and no value beside none", () => {
    renderModule("capital-structure");
    const item = within(groups()[1] as HTMLElement).getAllByRole("listitem")[2] as HTMLElement;
    expect(within(item).getByText("Withheld")).toBeVisible();
    expect(item).not.toHaveTextContent(/n\.a\./);
  });

  it("draws no trace control where the mock draws none, and one where a test carries a trace", () => {
    renderModule("capital-structure");
    expect(within(tests()).queryAllByRole("button")).toHaveLength(0);
    cleanup();
    const library = withRecords((records) => {
      const group = ((records.find((r) => r["kind"] === "status") as Json)["groups"] as Json[])[0];
      (group?.["items"] as Json[])[0] = {
        ...((group?.["items"] as Json[])[0] as Json),
        trace: "cs-term-loan",
        note: "The certificate was due on 15 January.",
      };
    });
    renderModule("capital-structure", "2026-09-30", library);
    expect(
      within(tests())
        .getAllByRole("button")
        .map((b) => b.getAttribute("aria-label")),
    ).toEqual(["Show sources for this test"]);
    expect(within(tests()).getByText("The certificate was due on 15 January.")).toBeVisible();
  });

  it("sets the two blocks side by side from 1200px and stacked below", () => {
    renderModule("capital-structure");
    const row = tests().parentElement;
    expect(row).toHaveClass("grid-cols-1", "min-[1200px]:grid-cols-2");
    expect(region("Facility terms").closest("[data-section]")?.parentElement).toBe(row);
  });
});

describe("Module, the statement by year", () => {
  const statement = () => region("Debt and leverage by year");
  const table = () => within(statement()).getByRole("table", { name: "Debt and leverage by year" });
  const cells = (row: HTMLElement) => within(row).getAllByRole("cell");

  it("draws the mock's years and five lines, each figure as delivered, 2022 EBITDA as n.a.", () => {
    renderModule("capital-structure");
    const rows = within(table()).getAllByRole("row");
    expect(
      within(rows[0] as HTMLElement)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["USD m, year to 30 Sep", "2022", "2023", "2024", "2025", "2026"]);
    expect(
      rows
        .slice(1)
        .map((r) => [
          within(r).getByRole("rowheader").textContent,
          ...cells(r).map((c) => c.textContent),
        ]),
    ).toEqual([
      ["Gross debt", "2,010", "2,120", "2,190", "2,310", "2,398"],
      ["Cash", "95", "120", "88", "146", "162"],
      ["Net debt", "1,915", "2,000", "2,102", "2,164", "2,236"],
      ["EBITDA", "n.a.not available", "356", "398", "441", "486"],
      ["Net leverage", "n.a.not available", "5.6x", "5.3x", "4.9x", "4.6x"],
    ]);
  });

  it("holds the first column while the table scrolls inside its own region", () => {
    renderModule("capital-structure");
    const scroller = table().parentElement as HTMLElement;
    expect(scroller).toHaveClass("overflow-x-auto");
    expect(within(table()).getAllByRole("columnheader")[0]).toHaveClass("sticky", "left-0");
    for (const header of within(table()).getAllByRole("rowheader")) {
      expect(header).toHaveClass("sticky", "left-0", "bg-surface-card");
    }
    for (const cell of within(table()).getAllByRole("cell")) {
      expect(cell).toHaveClass("text-right", "tabular-nums");
    }
  });

  it("draws the basis note under the table, and no trend column or Bars toggle", () => {
    renderModule("capital-structure");
    expect(
      within(statement()).getByText(
        "EBITDA for 2022 is not available on the current basis, so that year’s leverage is n.a.",
      ),
    ).toBeVisible();
    expect(within(statement()).queryByText(/trend/i)).toBeNull();
    expect(screen.queryByRole("radio", { name: /bars|figures/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Bars|Figures)$/ })).toBeNull();
  });

  it("draws a trace control only where the block carries a trace", () => {
    renderModule("capital-structure");
    expect(within(statement()).queryAllByRole("button")).toHaveLength(0);
    cleanup();
    const library = withRecords((records) => {
      (records.find((r) => r["kind"] === "statement") as Json)["trace"] = "cs-net-debt";
    });
    renderModule("capital-structure", "2026-09-30", library);
    const buttons = within(statement()).getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Show sources for this table",
    ]);
  });

  it("reveals the block's trace control on hover of the table, as the other blocks do", () => {
    const library = withRecords((records) => {
      (records.find((r) => r["kind"] === "statement") as Json)["trace"] = "cs-net-debt";
    });
    renderModule("capital-structure", "2026-09-30", library);
    const button = within(statement()).getByRole("button", {
      name: "Show sources for this table",
    });
    expect(button.closest('[class~="group/trace"]')).toBe(
      table().closest('[class~="group/trace"]'),
    );
    expect(table().closest('[class~="group/trace"]')).not.toBeNull();
  });

  it("keeps n.a. and the badges at regular weight in an emphasised line, and values semibold", () => {
    const library = withRecords((records) => {
      const rows = (records.find((r) => r["kind"] === "statement") as Json)["rows"] as Json[];
      (rows[1] as Json)["cells"] = [
        null,
        { kind: "withheld", reason: null },
        { kind: "gap", reason: "Not read." },
        { kind: "value", text: "0", at: 0 },
        { kind: "value", text: "162", at: 162 },
      ];
      (rows[1] as Json)["emphasis"] = true;
    });
    renderModule("capital-structure", "2026-09-30", library);
    const line = within(table()).getAllByRole("row")[2] as HTMLElement;
    const [missing, withheld, gap, zero, value] = cells(line);
    for (const cell of [missing, withheld, gap]) expect(cell).not.toHaveClass("font-semibold");
    for (const cell of [zero, value]) expect(cell).toHaveClass("font-semibold");
  });

  it("draws zero as zero, a withheld figure, a gap and an emphasised line as delivered", () => {
    const library = withRecords((records) => {
      const rows = (records.find((r) => r["kind"] === "statement") as Json)["rows"] as Json[];
      (rows[1] as Json)["cells"] = [
        { kind: "value", text: "0", at: 0 },
        null,
        { kind: "withheld", reason: null },
        { kind: "gap", reason: "Not read." },
        { kind: "value", text: "162", at: 162 },
      ];
      (rows[2] as Json)["emphasis"] = true;
    });
    renderModule("capital-structure", "2026-09-30", library);
    const rows = within(table()).getAllByRole("row");
    expect(cells(rows[2] as HTMLElement).map((c) => c.textContent)).toEqual([
      "0",
      "n.a.not available",
      "Withheld",
      "Not established for this run",
      "162",
    ]);
    expect(within(rows[3] as HTMLElement).getByRole("rowheader")).toHaveClass("font-semibold");
    expect(within(rows[2] as HTMLElement).getByRole("rowheader")).not.toHaveClass("font-semibold");
  });
});

describe("Module, the debt stack, maturities and headroom tables", () => {
  const card = (name: string) => region(name);
  const tableOf = (name: string) => within(card(name)).getByRole("table", { name });
  const body = (name: string) =>
    within(tableOf(name))
      .getAllByRole("row")
      .slice(1)
      .map((r) => [
        within(r).getByRole("rowheader").textContent,
        ...within(r)
          .getAllByRole("cell")
          .map((c) => c.textContent),
      ]);
  const head = (name: string) =>
    within(within(tableOf(name)).getAllByRole("row")[0] as HTMLElement)
      .getAllByRole("columnheader")
      .map((h) => h.textContent);

  it("draws the debt stack by rank with its basis note, its footnote and one trace control", () => {
    renderModule("capital-structure");
    expect(
      within(card("Debt stack")).getByRole("heading", { level: 3, name: "Debt stack" }),
    ).toBeVisible();
    expect(
      within(card("Debt stack")).getByText("USD 2,398m gross debt at 30 Sep 2026, by rank"),
    ).toBeVisible();
    expect(head("Debt stack")).toEqual(["Debt", "Rank and maturity", "Amount"]);
    expect(body("Debt stack")).toEqual([
      ["Term loan B", "Secured, due 2030", "USD 1,150m"],
      ["Senior secured notes", "Secured, due 2031", "USD 600m"],
      ["Senior unsecured notes", "Unsecured, due 2028", "USD 310m"],
      ["Leases", "Schedule n.a.", "USD 298m"],
      ["Other", "Due 2027", "USD 40m"],
    ]);
    expect(
      within(card("Debt stack")).getByText(
        "Basis: drawn amounts at face value; leases as reported.",
      ),
    ).toBeVisible();
    expect(
      within(card("Debt stack"))
        .getAllByRole("button")
        .map((b) => b.getAttribute("aria-label")),
    ).toEqual(["Show sources for the debt stack"]);
  });

  it("draws the maturities as the mock's table: 2029 as 0 beside leases as n.a., with no footnote", () => {
    renderModule("capital-structure");
    expect(head("Maturities by year")).toEqual(["Year", "Falls due", "Amount, USD m"]);
    expect(body("Maturities by year")).toEqual([
      ["2027", "Other debt", "40"],
      ["2028", "Senior unsecured notes", "310"],
      ["2029", "Nothing", "0"],
      ["2030", "Term loan B", "1,150"],
      ["2031", "Senior secured notes", "600"],
      ["Leases", "Schedule not in the files", "n.a.not available"],
    ]);
    expect(within(card("Maturities by year")).getByText("USD m, calendar years")).toBeVisible();
    expect(card("Maturities by year").querySelectorAll("p")).toHaveLength(1);
    expect(
      within(card("Maturities by year")).getByRole("button", {
        name: "Show sources for maturities",
      }),
    ).toBeVisible();
  });

  it("draws the headroom with the receivables test as the kit's Withheld, and no note", () => {
    renderModule("capital-structure");
    const name = "Headroom against covenant and rating triggers";
    expect(head(name)).toEqual(["Test", "Kind of limit", "Standing against the limit"]);
    expect(body(name)).toEqual([
      ["First-lien net leverage", "Springing covenant, maximum", "3.3x against 6.5x"],
      ["Net leverage", "Downgrade trigger, maximum", "4.6x against 5.5x"],
      ["Interest cover", "Downgrade trigger, minimum", "2.4x against 2.0x"],
      ["Receivables facility", "Availability test", "Withheld"],
    ]);
    expect(card(name).querySelectorAll("p")).toHaveLength(0);
    expect(
      within(card(name)).getByRole("button", { name: "Show sources for headroom" }),
    ).toBeVisible();
  });

  it("draws no Chart or Table toggle, since no chart side is drawn", () => {
    renderModule("capital-structure");
    expect(screen.queryByRole("radio", { name: /^(Chart|Table)$/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^(Chart|Table)$/ })).toBeNull();
  });

  it("sets text columns to the left and figures to the right, as delivered", () => {
    renderModule("capital-structure");
    const wrapper = tableOf("Maturities by year").parentElement as HTMLElement;
    expect(wrapper.parentElement).toHaveClass("[&_tr>:nth-child(2)]:text-left");
    expect(wrapper.parentElement).not.toHaveClass("[&_tr>:nth-child(3)]:text-left");
    expect(wrapper.parentElement).not.toHaveClass("[&_tr>:nth-child(1)]:text-left");
    for (const cell of within(tableOf("Maturities by year")).getAllByRole("cell")) {
      expect(cell).toHaveClass("tabular-nums");
    }
  });

  it("sets the cards in the order of the mock, between the measures and the facility terms", () => {
    renderModule("capital-structure");
    const headings = screen.getAllByRole("heading").map((h) => h.textContent);
    const order = [
      "Measures and their consequence",
      "Debt stack",
      "Maturities by year",
      "Headroom against covenant and rating triggers",
      "Liquidity walk, June to September 2026",
      "Leverage and margin against peers",
      "Interest cover against the peer range",
      "Facility terms",
    ].map((t) => headings.indexOf(t));
    expect(order).not.toContain(-1);
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });

  it("draws an emphasised row semibold with n.a. regular, zero as zero, and a gap as the badge", () => {
    const library = withRecords((records) => {
      const block = records.find((r) => r["kind"] === "chartTable") as Json;
      const rows = block["rows"] as Json[];
      (rows[2] as Json)["cells"] = [
        "Senior unsecured notes",
        "Unsecured, due 2028",
        { kind: "gap", reason: "Not read." },
      ];
      (rows[3] as Json)["cells"] = ["Leases", "Schedule n.a.", null];
      (rows[3] as Json)["emphasis"] = true;
      (rows[4] as Json)["cells"] = ["Other", "Due 2027", { kind: "value", text: "USD 0m", at: 0 }];
      block["footnotes"] = [];
      block["note"] = null;
    });
    renderModule("capital-structure", "2026-09-30", library);
    const wrapper = tableOf("Debt stack").parentElement?.parentElement as HTMLElement;
    expect(wrapper.className).toContain("[&_tbody_tr:nth-child(4)>*]:font-semibold");
    expect(wrapper.className).toContain("[&_tbody_tr:nth-child(4)_[aria-hidden=true]]:font-normal");
    expect(wrapper.className).not.toContain("nth-child(3)>*");
    expect(body("Debt stack")[2]?.[2]).toBe("Not established for this run");
    expect(body("Debt stack")[3]).toEqual(["Leases", "Schedule n.a.", "n.a.not available"]);
    expect(body("Debt stack")[4]).toEqual(["Other", "Due 2027", "USD 0m"]);
    expect(card("Debt stack").querySelectorAll("p")).toHaveLength(0);
  });
});

describe("Module, the liquidity walk and the peer tables", () => {
  const card = (name: string) => region(name);
  const rowsOf = (name: string) =>
    within(within(card(name)).getByRole("table", { name }))
      .getAllByRole("row")
      .map((r) => [...r.children].map((c) => c.textContent));
  const notes = (name: string) => [...card(name).querySelectorAll("p")].map((p) => p.textContent);
  const WALK = "Liquidity walk, June to September 2026";
  const SCATTER = "Leverage and margin against peers";
  const RANGE = "Interest cover against the peer range";

  it("draws the liquidity walk as its table, the totals as the module wrote them", () => {
    renderModule("capital-structure");
    expect(rowsOf(WALK)).toEqual([
      ["Step", "Effect", "USD m"],
      ["30 Jun 2026", "Total", "455"],
      ["Free cash flow", "Inflow", "+96"],
      ["Purchase", "Outflow", "\u2212140"],
      ["Dividends", "Outflow", "\u221220"],
      ["Other", "Inflow", "+21"],
      ["30 Sep 2026", "Total", "412"],
    ]);
    expect(notes(WALK)).toEqual(["USD m"]);
    const wrapper = within(card(WALK)).getByRole("table").parentElement
      ?.parentElement as HTMLElement;
    expect(wrapper.className).toContain("[&_tbody_tr:nth-child(1)>*]:font-semibold");
    expect(wrapper.className).toContain("[&_tbody_tr:nth-child(6)>*]:font-semibold");
    expect(wrapper.className).not.toContain("nth-child(2)>*");
    expect(wrapper.className).toContain("[&_tr>:nth-child(2)]:text-left");
  });

  it("draws the peer scatter with Peer E's margin as n.a. and the delivered not-plotted footnote", () => {
    renderModule("capital-structure");
    expect(rowsOf(SCATTER)).toEqual([
      ["Company", "Net leverage", "EBITDA margin, %"],
      ["Halden", "4.6x", "23.1"],
      ["Peer A", "3.2x", "19.6"],
      ["Peer B", "3.7x", "18.0"],
      ["Peer C", "4.2x", "16.0"],
      ["Peer D", "5.2x", "14.4"],
      ["Peer E", "3.5x", "n.a.not available"],
    ]);
    expect(notes(SCATTER)).toEqual([
      "Five listed peers, latest financial year",
      "Not plotted: Peer E (margin n.a.)",
    ]);
  });

  it("draws the peer range with the secured leverage band as n.a. and the delivered sentence", () => {
    renderModule("capital-structure");
    expect(rowsOf(RANGE)).toEqual([
      ["Measure", "Peer low", "Peer high", "Halden"],
      ["Interest cover", "2.1x", "5.8x", "2.4x"],
      ["Secured leverage", "n.a.not available", "n.a.not available", "3.3x"],
    ]);
    expect(notes(RANGE)).toEqual(["Near the bottom of the range: only one peer is lower."]);
  });

  it("opens each block's own drawer from its one trace control", () => {
    renderModule("capital-structure");
    for (const [name, label, title] of [
      [
        WALK,
        "Show sources for the liquidity walk",
        "Sources for the liquidity walk in this module",
      ],
      [SCATTER, "Show sources for the peer scatter", "Sources for the peer scatter in this module"],
      [RANGE, "Show sources for the peer range", "Sources for the peer range in this module"],
    ] as const) {
      const buttons = within(card(name)).getAllByRole("button");
      expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([label]);
      fireEvent.click(buttons[0] as HTMLElement);
      expect(screen.getByRole("dialog", { name: title })).toBeVisible();
      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    }
  });

  it("sets the scatter and the range side by side from 1200px, stacked below, and the rest alone", () => {
    renderModule("capital-structure");
    const row = card(RANGE).parentElement as HTMLElement;
    expect(row).toHaveClass("grid", "grid-cols-1", "gap-6", "min-[1200px]:grid-cols-2");
    expect(card(SCATTER).parentElement?.parentElement).toBe(row);
    for (const name of ["Debt stack", "Maturities by year", WALK]) {
      const around = card(name).parentElement as HTMLElement;
      expect(around.className).not.toContain("grid-cols-2");
      expect(around.parentElement?.className).not.toContain("grid-cols-2");
    }
  });

  it("keeps the run consistent: the tables read as the headline figures and the statement do", () => {
    renderModule("capital-structure");
    const page = document.body.textContent;
    const total = (name: string, label: string, column: number) => {
      const row = rowsOf(name).find((r) => r[0] === label);
      return row?.[column];
    };
    expect(total(WALK, "30 Sep 2026", 2)).toBe("412");
    expect(within(region("Measures and their consequence")).getByText("USD 412m")).toBeVisible();
    expect(total(SCATTER, "Halden", 1)).toBe("4.6x");
    expect(total(RANGE, "Secured leverage", 3)).toBe("3.3x");
    expect(total("Maturities by year", "2028", 2)).toBe("310");
    expect(page).toContain("USD 310m unsecured notes");
    expect(card("Debt stack")).toHaveTextContent("USD 2,398m gross debt at 30 Sep 2026");
    expect(total("Debt and leverage by year", "Gross debt", 5)).toBe("2,398");
  });
});

describe("Module, the hedge expiries gap", () => {
  const hedges = () => region("Hedge expiries");

  it("draws the kit's gap panel with the module's reason, and no chart or figure", () => {
    renderModule("capital-structure");
    expect(
      within(hedges()).getByRole("heading", { level: 3, name: "Hedge expiries" }),
    ).toBeVisible();
    expect(within(hedges()).getByText("Not established for this run")).toBeVisible();
    expect(
      within(hedges()).getByText(
        "The hedge schedule was not among the files provided. The module states that interest rate swaps exist but could not establish their amounts or expiry dates, so no chart is drawn.",
      ),
    ).toBeVisible();
    expect(within(hedges()).queryAllByRole("button")).toHaveLength(0);
    expect(within(hedges()).queryByRole("table")).toBeNull();
  });
});

describe("Module, the data module as a whole", () => {
  it("draws the trace controls the mock shows, each named as the mock names it", () => {
    renderModule("capital-structure");
    expect(sourceButtons().map((b) => b.getAttribute("aria-label"))).toEqual([
      "Show sources for the bottom line",
      ...Array<string>(3).fill("Show sources for this finding"),
      ...Array<string>(6).fill("Show sources for this figure"),
      ...Array<string>(3).fill("Show sources for this measure"),
      "Show sources for the debt stack",
      "Show sources for maturities",
      "Show sources for headroom",
      "Show sources for the liquidity walk",
      "Show sources for the peer scatter",
      "Show sources for the peer range",
      ...Array<string>(7).fill("Show sources for this fact"),
      ...Array<string>(3).fill("Show sources for this limitation"),
    ]);
  });

  it("turns every control on with Show sources, as the mock draws this page", () => {
    const { container } = renderModule("capital-structure");
    const toggle = screen.getByRole<HTMLInputElement>("switch", { name: "Show sources" });
    if (!toggle.checked) fireEvent.click(toggle);
    expect(container.querySelector("[data-sources]")).toHaveAttribute("data-sources", "on");
    expect(sourceButtons()).toHaveLength(29);
  });

  it("opens the drawer of the bottom line, a finding and a limitation by their own traces", () => {
    renderModule("capital-structure");
    const buttons = sourceButtons();
    for (const [index, title] of [
      [0, "Sources for the capital structure bottom line"],
      [3, "Sources for the capacity finding"],
      [28, "Sources for the lease schedule limitation"],
    ] as const) {
      fireEvent.click(buttons[index] as HTMLElement);
      expect(screen.getByRole("dialog", { name: title })).toBeVisible();
      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    }
  });

  it("shows no audit material and no trace code", () => {
    const { container } = renderModule("capital-structure");
    expect([container.innerHTML, container.textContent].join(" ")).not.toMatch(
      /T-\d{4}|C-\d{4}|\.pdf|hash|cs-/i,
    );
  });
});

describe("Module, the navigator of the data module", () => {
  it("moves focus to the heading of the block each entry names", () => {
    renderModule("capital-structure");
    Element.prototype.scrollIntoView = vi.fn();
    for (const [entry, heading] of [
      ["Debt stack and maturities", "Debt stack"],
      ["Headroom", "Headroom against covenant and rating triggers"],
      ["Liquidity walk", "Liquidity walk, June to September 2026"],
      ["Against peers", "Leverage and margin against peers"],
      ["Terms and tests", "Facility terms"],
      ["Hedges", "Hedge expiries"],
    ] as const) {
      fireEvent.click(within(nav()).getByRole("button", { name: entry }));
      expect(screen.getByRole("heading", { name: heading })).toHaveFocus();
    }
    Reflect.deleteProperty(Element.prototype, "scrollIntoView");
  });

  it("lists the entries the blocks name, once each, in page order", () => {
    renderModule("capital-structure");
    expect(
      within(within(nav()).getAllByRole("list")[0] as HTMLElement)
        .getAllByRole("button")
        .map((s) => s.textContent),
    ).toEqual([
      "Bottom line",
      "Key findings",
      "Headline figures",
      "Debt stack and maturities",
      "Headroom",
      "Liquidity walk",
      "Against peers",
      "Terms and tests",
      "Hedges",
      "Limitations",
    ]);
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
      issuers: {
        runs: {
          modules: unknown[];
          head: Json;
          overview: Json;
          changes: Json;
          evidence: {
            moduleFilter: unknown[];
            sources: { files: { readers: unknown }[] };
            gaps: { groups: unknown[] };
            tabs: Json;
          };
        }[];
      }[];
    };
    const run = slice.issuers[0]?.runs[3] as (typeof slice.issuers)[0]["runs"][0];
    run.modules = [];
    run.evidence.moduleFilter = [];
    for (const file of run.evidence.sources.files) file.readers = { shown: [], more: null };
    run.evidence.gaps.groups = [];
    run.evidence.tabs["gaps"] = "0";
    (run.overview["limitations"] as { gapsLink: Json }).gapsLink["label"] =
      "See the 0 gaps in Evidence";
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

describe("the module page's remount key", () => {
  // Route params are decoded, so an id holds a "/" when its link carried "%2F" (links.ts encodes
  // each segment): these addresses are different pages that a "/" join would key alike.
  it("differs for triples that a slash join would run together", () => {
    expect(moduleViewKey("a/b", "c", "d")).not.toBe(moduleViewKey("a", "b/c", "d"));
    expect(moduleViewKey("a", "b/c", "d")).not.toBe(moduleViewKey("a", "b", "c/d"));
    expect(moduleViewKey("a", "b", "c")).toBe(moduleViewKey("a", "b", "c"));
  });
});
