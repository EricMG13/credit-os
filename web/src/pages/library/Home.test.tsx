import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
import { appliedLabel } from "./parts/FilterBar";
import { routes } from "./routes";

type Json = Record<string, unknown>;
type Slice = { home: Json & { cards: Json[] }; issuers: Json[] };

const fixture = JSON.parse(
  readFileSync(
    path.resolve(import.meta.dirname, "..", "..", "..", "fixtures", "library.json"),
    "utf8",
  ),
) as { issuers: LibraryData["issuers"]; slice: Slice };

const fresh = (): Slice => structuredClone(fixture.slice);

function renderHome(library: unknown) {
  const data: LibraryData = { schema: "credit-os-data/1", issuers: fixture.issuers, library };
  const route = routes.find((r) => r.path === "/library/home");
  if (route === undefined) throw new Error("no /library route");
  return render(<SourceContext.Provider value={data}>{route.render({})}</SourceContext.Provider>);
}

/** The cards of the issuer grid, by issuer name. */
const card = (name: string) => screen.getByRole("link", { name: new RegExp(name) });

/** The hidden native select React Aria keeps beside each custom select: the testable control. */
function pick(label: RegExp, value: string) {
  const trigger = screen.getByRole("button", { name: label });
  const select = trigger.closest("div")?.querySelector("select");
  if (!select) throw new Error(`no select for ${String(label)}`);
  fireEvent.change(select, { target: { value: `option:${value}` } });
}

describe("the /library route", () => {
  it("declares the home once, titled Library", () => {
    expect(routes.filter((r) => r.path === "/library/home").map((r) => r.title)).toEqual([
      "Library",
    ]);
  });
});

describe("Library home, Cards side", () => {
  it("draws the delivered subtitle and a primary Start a run link to the run page", () => {
    renderHome(fixture.slice);
    expect(screen.getByText("Five issuers, each opening on its latest finished run")).toBeVisible();
    expect(screen.getByRole("link", { name: "Start a run" })).toHaveAttribute("href", "#/run");
  });

  it("draws the filter bar: search, three selects, and no filter applied", () => {
    renderHome(fixture.slice);
    expect(screen.getByRole("textbox", { name: "Search issuers" })).toBeInTheDocument();
    for (const name of ["Sector: All", "Pathway: All", "State: All"]) {
      expect(screen.getByRole("button", { name: new RegExp(name) })).toBeInTheDocument();
    }
    expect(screen.getByText("No filter applied")).toBeInTheDocument();
  });

  it("draws a finished issuer as a card linking to its latest run's Overview", () => {
    renderHome(fixture.slice);
    const halden = card("Halden Aerostructures");
    expect(halden).toHaveAttribute("href", "#/library/halden-aerostructures/2026-09-30/overview");
    expect(
      within(halden).getByRole("heading", { level: 2, name: "Halden Aerostructures" }),
    ).toBeVisible();
    expect(within(halden).getByText("Aerospace components")).toBeVisible();
    expect(within(halden).getByText("Finished")).toBeVisible();
    expect(within(halden).getByText(/Stable credit with thin headroom/)).toBeVisible();
    expect(within(halden).getByText("As of 30 Sep 2026")).toBeVisible();
    expect(within(halden).getByText("Full review")).toBeVisible();
  });

  it("draws a running issuer with the two-date note and a badge that does not pulse", () => {
    const { container } = renderHome(fixture.slice);
    const corvane = card("Corvane Packaging");
    expect(within(corvane).getByText("Running")).toBeVisible();
    expect(
      within(corvane).getByText(
        "A new run as of 30 Sep 2026 is in progress. This is the run as of 30 Jun 2026.",
      ),
    ).toBeVisible();
    expect(container.querySelector(".status-halo")).toBeNull();
  });

  it("draws a failed issuer with its note", () => {
    renderHome(fixture.slice);
    const ardenne = card("Ardenne Cable");
    expect(within(ardenne).getByText("Failed")).toBeVisible();
    expect(
      within(ardenne).getByText(
        "The run as of 30 Sep 2026 failed. This is the run as of 31 Mar 2026.",
      ),
    ).toBeVisible();
  });

  it("draws a capped issuer with its gap lead and note", () => {
    renderHome(fixture.slice);
    const lumora = card("Lumora Health");
    expect(within(lumora).getByText("Capped")).toBeVisible();
    expect(
      within(lumora).getByText(/^Not established for this run: the run stopped at its cost cap/),
    ).toBeVisible();
    expect(
      within(lumora).getByText("Seven modules delivered; their findings can be read."),
    ).toBeVisible();
  });

  it("shows a long lead in full, without cutting it", () => {
    renderHome(fixture.slice);
    const lead = within(card("Tessaly Foods")).getByText(/^Weakening: private-label losses/);
    expect(lead.textContent).toBe(
      "Weakening: private-label losses in the two largest retail accounts, a third consecutive quarter of negative free cash flow and a facility that is now 70% drawn mean the springing covenant is likely to be tested at the December quarter end, earlier than management has guided.",
    );
    expect(lead.className).not.toMatch(/truncate|line-clamp|text-ellipsis/);
  });

  it("draws the loading card as a static skeleton marked busy", () => {
    const { container } = renderHome(fixture.slice);
    const loading = screen.getByLabelText("Loading issuer");
    expect(loading).toHaveAttribute("aria-busy", "true");
    expect(loading.tagName).not.toBe("A");
    expect(container.querySelector(".animate-pulse")).toBeNull();
  });

  it("exposes the delivered progress text and no computed percentage", () => {
    renderHome(fixture.slice);
    const bars = screen.getAllByRole("progressbar");
    expect(bars).toHaveLength(5);
    const halden = within(card("Halden Aerostructures")).getByRole("progressbar");
    expect(halden).toHaveAccessibleName("12 of 13 modules");
    expect(halden.parentElement?.textContent).toBe("12 of 13 modules");
    for (const bar of bars) expect(bar.parentElement?.textContent).not.toMatch(/%/);
  });

  it("puts no audit material in any attribute, and only slug links in hrefs", () => {
    const { container } = renderHome(fixture.slice);
    const audit = /CP-\d|\b[0-9a-f]{12,}\b|\.(pdf|xlsx|md|json)\b|sha\d*[:-]|run[-_]?code/i;
    for (const element of container.querySelectorAll("*")) {
      for (const attr of Array.from(element.attributes)) {
        if (attr.name !== "class" && attr.name !== "style") expect(attr.value).not.toMatch(audit);
        if (attr.name === "href") {
          expect(attr.value).toMatch(
            /^#\/(run|library\/[a-z-]+\/(history|\d{4}-\d{2}-\d{2}\/overview))$/,
          );
        }
      }
    }
  });

  it("has one h1, Library, and no skipped heading level", () => {
    renderHome(fixture.slice);
    expect(screen.getByRole("heading", { level: 1, name: "Library" })).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const rest = screen.getAllByRole("heading").filter((h) => h.tagName !== "H1");
    expect(rest.every((h) => h.tagName === "H2")).toBe(true);
  });
  it("draws a card without a finished run as a link to the issuer's history", () => {
    const slice = fresh();
    slice.home.cards[3] = { ...slice.home.cards[3], href: null };
    renderHome(slice);
    expect(card("Ardenne Cable")).toHaveAttribute("href", "#/library/ardenne-cable/history");
  });

  it("draws the Layout toggle with Cards chosen first", () => {
    renderHome(fixture.slice);
    const group = screen.getByRole("radiogroup", { name: "Layout" });
    expect(within(group).getByRole("radio", { name: "Cards" })).toBeChecked();
    expect(within(group).getByRole("radio", { name: "List" })).not.toBeChecked();
    expect(screen.queryByRole("grid", { name: "Issuers" })).toBeNull();
  });

  it("says the data file holds no library pages when it has no library member, under the h1", () => {
    renderHome(undefined);
    expect(screen.getByRole("heading", { level: 1, name: "Library" })).toBeVisible();
    expect(screen.getByText("This data file holds no library pages")).toBeVisible();
    expect(screen.queryByText("Library data is missing")).toBeNull();
  });

  it("names the failing path when it is handed an invalid slice", () => {
    const slice = fresh();
    slice.home.cards[1] = { ...slice.home.cards[1], note: 7 };
    renderHome(slice);
    expect(screen.getByText(/home\.cards\[1\]\.note/)).toBeVisible();
    expect(screen.queryByRole("link", { name: /Halden/ })).toBeNull();
  });
});

describe("narrowing the cards", () => {
  const shown = () =>
    screen
      .getAllByRole("heading", { level: 2 })
      .map((h) => h.textContent)
      .filter((name) => name !== "Loading issuer");

  it("matches the search against names, ignoring case, and counts it as one filter", () => {
    renderHome(fixture.slice);
    fireEvent.change(screen.getByRole("textbox", { name: "Search issuers" }), {
      target: { value: "haLDEN" },
    });
    expect(shown()).toEqual(["Halden Aerostructures"]);
    expect(screen.getByText("1 filter applied")).toBeInTheDocument();
    expect(screen.queryByLabelText("Loading issuer")).toBeNull();
  });

  it("matches a select's option exactly", () => {
    renderHome(fixture.slice);
    pick(/Sector: All/, "Packaged food");
    expect(shown()).toEqual(["Tessaly Foods"]);
    pick(/Pathway/, "Monitoring update");
    expect(shown()).toEqual(["Tessaly Foods"]);
    expect(screen.getByText("2 filters applied")).toBeInTheDocument();
    pick(/State/, "Failed");
    expect(screen.getByText("No issuer matches")).toBeInTheDocument();
    expect(screen.getByText("3 filters applied")).toBeInTheDocument();
  });

  it("filters by run state", () => {
    renderHome(fixture.slice);
    pick(/State: All/, "Capped");
    expect(shown()).toEqual(["Lumora Health"]);
  });

  it("says no issuer matches and clears every filter from the empty state", () => {
    renderHome(fixture.slice);
    fireEvent.change(screen.getByRole("textbox", { name: "Search issuers" }), {
      target: { value: "zzz" },
    });
    pick(/Sector: All/, "Packaged food");
    expect(screen.getByText("No issuer matches")).toBeInTheDocument();
    expect(screen.getByText("2 filters applied")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(shown()).toHaveLength(5);
    expect(screen.getByText("No filter applied")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Search issuers" })).toHaveValue("");
    expect(screen.getByRole("button", { name: /Sector: All/ })).toBeInTheDocument();
  });
});

describe("Library home, other states", () => {
  it("says No runs yet, with its sentence and Start a run, when the library holds no issuer", () => {
    const slice = fresh();
    slice.home = { ...slice.home, subtitle: "No issuers yet", cards: [] };
    slice.issuers = [];
    renderHome(slice);
    expect(screen.getByText("No issuers yet")).toBeVisible();
    expect(screen.getByRole("heading", { level: 2, name: "No runs yet" })).toBeVisible();
    expect(
      screen.getByText(
        "A run reads an issuer’s files and writes its report here. Start one to add the first issuer.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Start a run" })).toHaveAttribute("href", "#/run");
    expect(screen.queryByRole("textbox", { name: "Search issuers" })).toBeNull();
  });
});

describe("carried fixes from task 1", () => {
  it("throws for a filter count with no delivered label, and returns the label otherwise", () => {
    expect(appliedLabel(["none", "one"], 1)).toBe("one");
    expect(() => appliedLabel(["none", "one"], 2)).toThrow(RangeError);
  });

  it("lists plain option text while the closed control keeps its prefix", () => {
    renderHome(fixture.slice);
    const trigger = screen.getByRole("button", { name: /Sector: All/ });
    const select = trigger.closest("div")?.querySelector("select");
    const options = Array.from(select?.options ?? []).map((o) => o.textContent);
    // React Aria's native select leads with one blank placeholder option.
    expect(options.slice(1)).toEqual([
      "All",
      "Aerospace components",
      "Cable and broadband",
      "Outpatient clinics",
      "Packaged food",
      "Rigid packaging",
    ]);
    pick(/Sector: All/, "Packaged food");
    expect(screen.getByRole("button", { name: /Sector: Packaged food/ })).toBeInTheDocument();
  });

  it("sizes the selects to their content and caps the search at its own width", () => {
    renderHome(fixture.slice);
    const search = screen.getByRole("textbox", { name: "Search issuers" });
    expect(search.closest(".max-w-full")?.className).toMatch(/w-\[280px\]/);
    for (const name of [/Sector: All/, /Pathway: All/, /State: All/]) {
      const root = screen.getByRole("button", { name }).closest("div");
      expect(root?.className).not.toMatch(/\bw-(60|72)\b/);
    }
  });

  it("draws the loading card with the mock's pills and thin bar", () => {
    renderHome(fixture.slice);
    const loading = screen.getByLabelText("Loading issuer");
    expect(loading.querySelectorAll(".rounded-full")).toHaveLength(3);
    expect(loading.querySelectorAll(".h-2")).toHaveLength(1);
  });
});

describe("Library home, List side", () => {
  const toList = () => {
    renderHome(fixture.slice);
    fireEvent.click(screen.getByRole("radio", { name: "List" }));
  };
  const table = () => screen.getByRole("grid", { name: "Issuers" });
  const names = () =>
    within(table())
      .getAllByRole("row")
      .slice(1)
      .map((row) => within(row).getAllByRole("link")[0]?.textContent);
  const row = (name: string) => {
    const found = within(table())
      .getAllByRole("row")
      .find((r) => within(r).queryByRole("link", { name }));
    if (!found) throw new Error(`no row for ${name}`);
    return found;
  };
  const head = (name: string) => within(table()).getByRole("columnheader", { name });
  const band = (measure: string, label: string) => {
    const trigger = screen.getByRole("button", { name: new RegExp(`^${measure}\\b`) });
    const select = trigger.closest("div")?.querySelector("select");
    if (!select) throw new Error(`no select for ${measure}`);
    fireEvent.change(select, { target: { value: `option:${label}` } });
  };

  it("draws one row per issuer with the delivered cells and no loading card", () => {
    toList();
    expect(screen.queryByLabelText("Loading issuer")).toBeNull();
    expect(
      within(table())
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual([
      "Issuer",
      "Sector",
      "State",
      "As of",
      "Pathway",
      "Modules",
      "Leverage",
      "Net leverage",
      "Interest coverage",
    ]);
    expect(names()).toHaveLength(5);
    const halden = row("Halden Aerostructures");
    expect(within(halden).getByRole("link")).toHaveAttribute(
      "href",
      "#/library/halden-aerostructures/2026-09-30/overview",
    );
    for (const text of ["Aerospace components", "Finished", "As of 30 Sep 2026", "Full review"]) {
      expect(within(halden).getByText(text)).toBeVisible();
    }
    expect(within(halden).getByText("12 of 13 modules")).toBeVisible();
    // WBR-01 ruling: the row carries its run's own figures, company-adjusted; no gross leverage.
    for (const text of ["4.6x adj.", "2.4x adj."]) {
      expect(within(halden).getByRole("button", { name: text })).toBeVisible();
    }
    expect(within(halden).getByRole("button", { name: "4.6x adj." })).toHaveAccessibleDescription(
      "Company-adjusted EBITDA, year to 30 Sep 2026",
    );
    expect(within(halden).getAllByText("n.a.")).toHaveLength(1);
  });

  it("marks an adjusted figure adj. and describes it with its period", () => {
    toList();
    const tessaly = row("Tessaly Foods");
    const lev = within(tessaly).getByRole("button", { name: "5.6x adj." });
    expect(lev).toHaveAccessibleDescription(
      "Adjusted EBITDA (management definition), year to 30 Sep 2026",
    );
    expect(within(tessaly).getByRole("button", { name: "5.1x adj." })).toHaveAccessibleDescription(
      "Adjusted EBITDA (management definition). Period not recorded",
    );
    expect(within(tessaly).getByRole("button", { name: "1.9x" })).toBeVisible();
  });

  it("draws not recorded as n.a. and a zero figure as 0.0x", () => {
    toList();
    expect(within(row("Lumora Health")).getAllByText("n.a.")).toHaveLength(2);
    expect(within(row("Ardenne Cable")).getAllByText("n.a.")).toHaveLength(1);
    expect(within(row("Corvane Packaging")).getByRole("button", { name: "0.0x" })).toBeVisible();
    expect(within(row("Corvane Packaging")).queryByText("n.a.")).toBeNull();
  });

  it("sorts by figure, with adjusted and missing figures last in either direction", () => {
    toList();
    fireEvent.click(head("Leverage"));
    expect(head("Leverage")).toHaveAttribute("aria-sort", "ascending");
    expect(names()).toEqual([
      "Corvane Packaging",
      "Ardenne Cable",
      "Halden Aerostructures",
      "Tessaly Foods",
      "Lumora Health",
    ]);
    fireEvent.click(head("Leverage"));
    expect(head("Leverage")).toHaveAttribute("aria-sort", "descending");
    expect(names()).toEqual([
      "Ardenne Cable",
      "Corvane Packaging",
      "Halden Aerostructures",
      "Tessaly Foods",
      "Lumora Health",
    ]);
  });

  it("sorts a zero figure ahead of the others, not with the missing ones", () => {
    toList();
    fireEvent.click(head("Net leverage"));
    expect(names().slice(0, 2)).toEqual(["Corvane Packaging", "Ardenne Cable"]);
  });

  it("delivers a count line for each measure, with and without the adjusted clause", () => {
    toList();
    expect(
      screen.getByText("Leverage recorded for 3 of 5 runs · 1 on adjusted EBITDA, not screened"),
    ).toBeVisible();
    expect(
      screen.getByText(
        "Net leverage recorded for 4 of 5 runs · 2 on adjusted EBITDA, not screened",
      ),
    ).toBeVisible();
    expect(
      screen.getByText(
        "Interest coverage recorded for 4 of 5 runs · 1 on adjusted EBITDA, not screened",
      ),
    ).toBeVisible();
  });

  it("applies a band: an adjusted or missing figure passes none, and its rows are listed", () => {
    toList();
    expect(screen.queryByRole("heading", { name: /^Hidden by/ })).toBeNull();
    band("Leverage", "Below 3.0x");
    expect(names()).toEqual(["Corvane Packaging"]);
    const heading = screen.getByRole("heading", {
      level: 2,
      name: "Hidden by Leverage: no figure recorded, or a figure on adjusted EBITDA",
    });
    const hidden = heading.parentElement;
    expect(
      within(hidden as HTMLElement)
        .getAllByRole("link")
        .map((l) => l.textContent),
    ).toEqual(["Halden Aerostructures", "Tessaly Foods", "Lumora Health"]);
    band("Leverage", "5.0x and above");
    expect(names()).toEqual(["Ardenne Cable"]);
  });

  it("names an adjusted interest coverage figure among the hidden rows (WBR-01 ruling)", () => {
    toList();
    band("Interest coverage", "4.0x and above");
    expect(names()).toEqual(["Corvane Packaging"]);
    expect(
      screen.getByRole("heading", {
        name: "Hidden by Interest coverage: no figure recorded, or a figure on adjusted EBITDA",
      }),
    ).toBeVisible();
  });

  it("passes a zero figure in the lowest band", () => {
    toList();
    band("Net leverage", "Below 3.0x");
    expect(names()).toEqual(["Corvane Packaging"]);
  });

  it("keeps the filters when the layout goes back to Cards", () => {
    toList();
    pick(/Sector: All/, "Packaged food");
    expect(names()).toEqual(["Tessaly Foods"]);
    fireEvent.click(screen.getByRole("radio", { name: "Cards" }));
    expect(screen.getByText("1 filter applied")).toBeInTheDocument();
    expect(screen.queryByRole("grid", { name: "Issuers" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Tessaly Foods",
    ]);
    fireEvent.click(screen.getByRole("radio", { name: "List" }));
    expect(names()).toEqual(["Tessaly Foods"]);
  });

  it("says no issuer matches when the search and bands leave nothing, and clears both", () => {
    toList();
    band("Leverage", "Below 3.0x");
    band("Interest coverage", "Below 2.0x");
    expect(screen.getByText("No issuer matches")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(names()).toHaveLength(5);
  });

  it("draws no audit material and no computed text beyond the delivered strings", () => {
    toList();
    const audit = /CP-\d|\b[0-9a-f]{12,}\b|\.(pdf|xlsx|md|json)\b/i;
    for (const element of table().querySelectorAll("*")) {
      for (const attr of Array.from(element.attributes)) {
        if (attr.name !== "class") expect(attr.value).not.toMatch(audit);
      }
    }
  });

  it("counts the chosen bands as applied filters, with one label for each count up to seven", () => {
    toList();
    band("Leverage", "Below 3.0x");
    expect(screen.getByText("1 filter applied")).toBeInTheDocument();
    band("Net leverage", "Below 3.0x");
    band("Interest coverage", "Below 2.0x");
    expect(screen.getByText("3 filters applied")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Search issuers" }), {
      target: { value: "a" },
    });
    pick(/Sector: All/, "Packaged food");
    pick(/Pathway: All/, "Monitoring update");
    pick(/State: All/, "Finished");
    expect(screen.getByText("7 filters applied")).toBeInTheDocument();
  });

  it("resets the bands when the layout goes back to Cards, where they narrow nothing", () => {
    toList();
    band("Leverage", "Below 3.0x");
    fireEvent.click(screen.getByRole("radio", { name: "Cards" }));
    expect(screen.getByText("No filter applied")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(5);
    expect(screen.getByLabelText("Loading issuer")).toBeVisible();
    fireEvent.click(screen.getByRole("radio", { name: "List" }));
    expect(names()).toHaveLength(5);
  });

  it("chooses the hidden-rows wording from the rows the band hid, not from the slice", () => {
    toList();
    fireEvent.change(screen.getByRole("textbox", { name: "Search issuers" }), {
      target: { value: "Lumora" },
    });
    band("Leverage", "Below 3.0x");
    expect(
      screen.getByRole("heading", { name: "Hidden by Leverage: no figure recorded" }),
    ).toBeVisible();
    fireEvent.change(screen.getByRole("textbox", { name: "Search issuers" }), {
      target: { value: "Tessaly" },
    });
    expect(
      screen.getByRole("heading", {
        name: "Hidden by Leverage: no figure recorded, or a figure on adjusted EBITDA",
      }),
    ).toBeVisible();
  });

  it("lets all nine columns fit: no clipping, dates and figures unbroken, tight padding", () => {
    toList();
    const region = screen.getByRole("region", { name: "Issuers" });
    expect(region).not.toHaveAttribute("tabindex");
    expect(region.className).toMatch(/overflow-x-auto/);
    expect(region).toContainElement(table());
    expect(table().className).toMatch(/w-max/);
    const cells = within(row("Halden Aerostructures")).getAllByRole("gridcell");
    for (const cell of cells) expect(cell.className).toMatch(/\bpx-3\b/);
    for (const text of ["As of 30 Sep 2026", "4.6x"]) {
      expect(within(row("Halden Aerostructures")).getByText(text).closest("td")?.className).toMatch(
        /whitespace-nowrap/,
      );
    }
    expect(within(table()).getAllByRole("columnheader")).toHaveLength(9);
  });
});
