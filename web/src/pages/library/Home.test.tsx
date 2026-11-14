import { readFileSync } from "node:fs";
import path from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import type { LibraryData } from "@/data";
import { SourceContext } from "../source";
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
  it("is declared once, titled Library", () => {
    expect(routes.map((r) => [r.path, r.title])).toEqual([["/library/home", "Library"]]);
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

  it("has no h1 of its own and no skipped heading level", () => {
    renderHome(fixture.slice);
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.getAllByRole("heading").every((h) => h.tagName === "H2")).toBe(true);
  });
  it("draws a card without a finished run as a link to the issuer's history", () => {
    const slice = fresh();
    slice.home.cards[3] = { ...slice.home.cards[3], href: null };
    renderHome(slice);
    expect(card("Ardenne Cable")).toHaveAttribute("href", "#/library/ardenne-cable/history");
  });

  it("draws no Cards or List toggle until the List side exists", () => {
    renderHome(fixture.slice);
    expect(screen.queryByRole("group", { name: "Layout" })).toBeNull();
    expect(screen.queryByText("List")).toBeNull();
  });

  it("says the library data is missing when the data file has no library member", () => {
    renderHome(undefined);
    expect(screen.getByText("Library data is missing")).toBeVisible();
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
