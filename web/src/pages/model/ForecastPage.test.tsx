import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { edited, fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const BASE = "#/model/transdigm/2025-06-30";
const F = ["runs", 0, "forecast"] as const;
const DRIVERS = "What drives each case";
const COVER = "Interest cover";
const PATHS = "EBITDA by case";
const WALK = "From EBITDA to free cash flow";
const WATCH = "What would change the forecast";

// Everything below is copied from the mock (Forecast), not read from the page code.
const DRIVER_TABLE = [
  ["Organic revenue growth", "-12%", "18%", "8.0%", "-4.0%"],
  ["EBITDA margin", "44%", "53%", "53.4%", "46.9%"],
  ["Capital expenditure, share of revenue", "1.6%", "2.4%", "2.1%", "1.7%"],
  ["Cash interest rate on debt", "5.2%", "7.1%", "5.3%", "6.0%"],
  ["Working capital days", "92", "118", "n.a.", "n.a."],
  ["Aftermarket share of revenue", "n.a.", "n.a.", "55%", "52%"],
] as const;
const COVER_TABLE = [
  ["Base case", "2.6x", "n.a.", "2.8x", "2.9x", "3.0x", "3.3x", "3.6x"],
  ["Downside case", "2.6x", "n.a.", "2.8x", "2.9x", "2.9x", "2.3x", "2.4x"],
] as const;
const PATH_TABLE = [
  ["Base case", "2,646", "3,395", "4,173", "4,560", "4,690", "5,080", "5,460"],
  ["Downside case", "2,646", "3,395", "4,173", "4,560", "4,560", "4,120", "4,350"],
] as const;
const WALK_TABLE = [
  ["EBITDA as defined", "5,080", "4,120"],
  ["Cash interest", "-1,560", "-1,790"],
  ["Cash tax", "-610", "-430"],
  ["Change in working capital", "-170", "60"],
  ["Capital expenditure", "-200", "-150"],
  ["Other cash items", "n.a.", "n.a."],
  ["Free cash flow", "2,540", "1,810"],
] as const;
const WALK_BASE = ["5,080", "-1,560", "-610", "-170", "-200", "2,540"];
const WALK_DOWN = ["4,120", "-1,790", "-430", "+60", "-150", "1,810"];

function renderAt(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/forecast`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

const figure = (name: string): HTMLElement => screen.getByRole("figure", { name });
const card = (name: string): HTMLElement =>
  must(figure(name).closest<HTMLElement>(".rounded-ds-lg"));
const choose = (name: string) => {
  fireEvent.click(screen.getByRole("radio", { name }));
};
const labels = (name: string, series?: string): string[] =>
  [...figure(name).querySelectorAll(".recharts-wrapper [data-label]")]
    .filter((el) => series === undefined || el.getAttribute("data-series") === series)
    .map((el) => el.textContent);
const cellText = (c: HTMLElement) => c.textContent.replace("not available", "");

function tableRows(name: string): string[][] {
  fireEvent.click(within(figure(name)).getByRole("radio", { name: "Table" }));
  return within(figure(name))
    .getAllByRole("row")
    .slice(1)
    .map((r) => [
      ...within(r)
        .getAllByRole("rowheader")
        .map((h) => h.textContent),
      ...within(r).getAllByRole("cell").map(cellText),
    ]);
}

describe("Forecast page: the shell and the cases", () => {
  it("orders the headings h1 (the issuer), h2 (the sections), h3 (the chart titles)", () => {
    renderAt(fixtureSlice());
    expect(screen.getAllByRole("heading").map((h) => [h.tagName, h.textContent])).toEqual([
      ["H1", "TransDigm Group"],
      ["H2", "Two cases"],
      ["H3", DRIVERS],
      ["H3", COVER],
      ["H3", PATHS],
      ["H2", "Cash flow in FY26"],
      ["H3", WALK],
    ]);
  });

  it("draws the run tabs with the delivered counts and marks Forecast current", () => {
    renderAt(fixtureSlice());
    const links = within(screen.getByRole("navigation", { name: "Pages" })).getAllByRole("link");
    expect(links.map((l) => [l.textContent, l.getAttribute("aria-current")])).toEqual([
      ["Overview", null],
      ["Changes5", null],
      ["Modules11", null],
      ["Forecast", "page"],
      ["Evidence", null],
    ]);
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "#/library/transdigm/2025-06-30/overview",
      "#/library/transdigm/2025-06-30/changes",
      "#/library/transdigm/2025-06-30/modules",
      `${BASE}/forecast`,
      ADDRESS,
    ]);
  });

  it("links the current Forecast tab to this page's own address", () => {
    renderAt(fixtureSlice());
    const nav = within(screen.getByRole("navigation", { name: "Pages" }));
    expect(nav.getByRole("link", { name: "Forecast" })).toHaveAttribute(
      "href",
      "#/model/transdigm/2025-06-30/forecast",
    );
  });

  it("sets a tab's count at the 13px caption size, not 12px", () => {
    renderAt(fixtureSlice());
    const count = must(screen.getByText("5").closest("span"));
    expect(count.classList.contains("text-caption")).toBe(true);
    expect(count.classList.contains("text-xs")).toBe(false);
  });

  it("draws the action 'Open the financial model' to the front page, and the Forecast breadcrumb", () => {
    renderAt(fixtureSlice());
    expect(screen.getByRole("link", { name: "Open the financial model" })).toHaveAttribute(
      "href",
      `${BASE}/front`,
    );
    expect(screen.queryByRole("link", { name: "Back to the report" })).toBeNull();
    const crumb = within(screen.getByRole("navigation", { name: "Breadcrumb" }));
    expect(crumb.getByText("Forecast")).toHaveAttribute("aria-current", "page");
    expect(crumb.queryByText("Financial model")).toBeNull();
  });

  it("draws the choice line and the two cards, the first chosen", () => {
    renderAt(fixtureSlice());
    expect(screen.getByText("Choose a case: every chart below follows it.")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Base case" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Downside case" })).not.toBeChecked();
    expect(
      screen.getByText(
        "Aftermarket sales grow 8% a year and margins hold near 53%. Cash builds on the balance sheet.",
      ),
    ).toBeInTheDocument();
  });
});

describe("Forecast page: what drives each case", () => {
  it("draws the rows, their range lines, both values and the legend", () => {
    renderAt(fixtureSlice());
    const chart = figure(DRIVERS);
    expect(
      within(chart).getByText(
        "Each FY26 assumption against the range seen over the past five years",
      ),
    ).toBeInTheDocument();
    expect(
      within(chart).getByText(
        "Working capital days could not be set for FY26. No five-year range exists for aftermarket share, so no strip is drawn.",
      ),
    ).toBeInTheDocument();
    const rows = [...chart.querySelectorAll<HTMLElement>("[data-row]")];
    expect(
      rows.map((r) => [
        r.querySelector("b")?.textContent,
        r.querySelector("[data-sub]")?.textContent,
        [...r.querySelectorAll("[data-value]")].map((v) => cellText(v as HTMLElement)),
      ]),
    ).toEqual([
      ["Organic revenue growth", "Past five years: -12% to 18%", ["8.0%", "-4.0%"]],
      ["EBITDA margin", "Past five years: 44% to 53%", ["53.4%", "46.9%"]],
      ["Capital expenditure, share of revenue", "Past five years: 1.6% to 2.4%", ["2.1%", "1.7%"]],
      ["Cash interest rate on debt", "Past five years: 5.2% to 7.1%", ["5.3%", "6.0%"]],
      ["Working capital days", "Past five years: 92 to 118", ["n.a.", "n.a."]],
      ["Aftermarket share of revenue", "Range n.a.", ["55%", "52%"]],
    ]);
    expect(
      within(within(chart).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Range over five years", "Base case assumption", "Downside case assumption"]);
  });

  it("draws a strip on five rows and two markers on four, none for the missing value or range", () => {
    renderAt(fixtureSlice());
    const chart = figure(DRIVERS);
    const row = (label: string) =>
      must(within(chart).getByText(label).closest<HTMLElement>("[data-row]"));
    expect(chart.querySelectorAll("[data-range]")).toHaveLength(5);
    expect(chart.querySelectorAll("[data-marker]")).toHaveLength(8);
    const wc = row("Working capital days");
    expect(wc.querySelector("[data-range]")).not.toBeNull();
    expect(wc.querySelector("[data-marker]")).toBeNull();
    expect(
      [...wc.querySelectorAll("[data-missing]")].map((m) => cellText(m as HTMLElement)),
    ).toEqual(["n.a.", "n.a."]);
    const after = row("Aftermarket share of revenue");
    expect(after.querySelector("[data-range]")).toBeNull();
    expect(after.querySelector("[data-marker]")).toBeNull();
    expect(after.querySelectorAll("[data-missing]")).toHaveLength(0);
  });

  it("puts a key glyph beside each present value and none beside n.a.", () => {
    renderAt(fixtureSlice());
    const chart = figure(DRIVERS);
    const glyphs = (label: string) =>
      must(within(chart).getByText(label).closest<HTMLElement>("[data-row]")).querySelectorAll(
        "[data-value] i",
      ).length;
    expect(glyphs("Organic revenue growth")).toBe(2);
    expect(glyphs("Working capital days")).toBe(0);
    expect(glyphs("Aftermarket share of revenue")).toBe(2);
  });

  it("places the strip and the two markers from the mock's data", () => {
    renderAt(fixtureSlice());
    const row = must(
      within(figure(DRIVERS))
        .getByText("Organic revenue growth")
        .closest<HTMLElement>("[data-row]"),
    );
    // Axis -15 to 20: the range -12 to 18 starts at 3/35 and is 30/35 wide; 8 is at 23/35, -4 at 11/35.
    const at = (el: Element | null, name: string) => Number(el?.getAttribute(name));
    expect(at(row.querySelector("[data-range]"), "data-left")).toBeCloseTo(8.5714, 3);
    expect(at(row.querySelector("[data-range]"), "data-width")).toBeCloseTo(85.7143, 3);
    expect(at(row.querySelector('[data-name="Base case assumption"]'), "data-left")).toBeCloseTo(
      65.7143,
      3,
    );
    expect(
      at(row.querySelector('[data-name="Downside case assumption"]'), "data-left"),
    ).toBeCloseTo(31.4286, 3);
  });

  it("draws both markers of a row in full colour, and the chosen case's wider and taller", () => {
    renderAt(fixtureSlice());
    const markers = () => [...figure(DRIVERS).querySelectorAll("[data-marker]")];
    expect(markers()).toHaveLength(8);
    const weight = (name: string) =>
      markers()
        .filter((m) => m.getAttribute("data-name") === name)
        .map((m) => m.classList.contains("w-1.5") && m.classList.contains("h-7"));
    expect(weight("Base case assumption")).toEqual([true, true, true, true]);
    expect(weight("Downside case assumption")).toEqual([false, false, false, false]);
    for (const m of markers()) expect(m.className).not.toMatch(/opacity/);
    choose("Downside case");
    expect(markers()).toHaveLength(8);
    expect(weight("Base case assumption")).toEqual([false, false, false, false]);
    expect(weight("Downside case assumption")).toEqual([true, true, true, true]);
  });

  it("sets the other case's values in the tertiary colour, the chosen case's not", () => {
    renderAt(fixtureSlice());
    const row = must(
      [...figure(DRIVERS).querySelectorAll<HTMLElement>("[data-row]")].find(
        (r) => r.querySelector("b")?.textContent === "EBITDA margin",
      ),
    );
    const tone = () =>
      [...row.querySelectorAll("[data-value]")].map((v) =>
        v.classList.contains("text-text-tertiary"),
      );
    expect(tone()).toEqual([false, true]);
    choose("Downside case");
    expect(tone()).toEqual([true, false]);
  });

  it("holds the five columns of the table with n.a. in the same cells", () => {
    renderAt(fixtureSlice());
    expect(tableRows(DRIVERS)).toEqual(DRIVER_TABLE.map((r) => [...r]));
    expect(
      within(figure(DRIVERS))
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Driver, FY26", "Range low", "Range high", "Base case", "Downside case"]);
  });
});

describe("Forecast page: interest cover and EBITDA by case", () => {
  it("draws the chosen case's line only, labelled from the mock, breaking at FY23", () => {
    renderAt(fixtureSlice());
    expect(labels(COVER)).toEqual(["2.6x", "2.8x", "2.9x", "3.0x", "3.3x", "3.6x"]);
    expect(within(figure(COVER)).getByText("Forecast")).toBeInTheDocument();
    expect(figure(COVER).querySelectorAll("[data-divider]")).toHaveLength(1);
    expect(within(figure(COVER)).getByText("n.a.")).toBeInTheDocument();
    expect(within(figure(COVER)).queryByRole("list", { name: "Legend" })).toBeNull();
    const path = must(figure(COVER).querySelector(".recharts-line-curve")).getAttribute("d") ?? "";
    expect(path.match(/M/g)).toHaveLength(2);
  });

  it("follows the chosen case: the downside line, with the same break", () => {
    renderAt(fixtureSlice());
    choose("Downside case");
    expect(labels(COVER)).toEqual(["2.6x", "2.8x", "2.9x", "2.9x", "2.3x", "2.4x"]);
    expect(within(figure(COVER)).getByText("n.a.")).toBeInTheDocument();
  });

  it("draws both EBITDA lines whichever case is chosen, with Last actual marked", () => {
    renderAt(fixtureSlice());
    const both = () => [labels(PATHS, "Actual, then base case"), labels(PATHS, "Downside case")];
    expect(both()).toEqual([
      ["2,646", "4,560", "5,460"],
      ["4,120", "4,350"],
    ]);
    expect(within(figure(PATHS)).getByText("Last actual")).toBeInTheDocument();
    choose("Downside case");
    expect(both()).toEqual([
      ["2,646", "4,560", "5,460"],
      ["4,120", "4,350"],
    ]);
    expect(
      within(within(figure(PATHS)).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Actual, then base case", "Downside case"]);
  });

  it("holds both cases in each table, with n.a. where the mock has it", () => {
    renderAt(fixtureSlice());
    expect(tableRows(COVER)).toEqual(COVER_TABLE.map((r) => [...r]));
    expect(tableRows(PATHS)).toEqual(PATH_TABLE.map((r) => [...r]));
    expect(
      within(figure(PATHS))
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["EBITDA as defined", "FY22", "FY23", "FY24", "LTM", "FY25E", "FY26E", "FY27E"]);
  });

  it("draws the basis lines under the charts", () => {
    renderAt(fixtureSlice());
    expect(
      within(figure(COVER)).getByText(
        "Cash interest for FY23 was not split out, so the line breaks there. It is not joined across the gap.",
      ),
    ).toBeInTheDocument();
    expect(
      within(figure(PATHS)).getByText("Both cases start from the twelve months to June 2025."),
    ).toBeInTheDocument();
  });

  it("sets both on a whole row, because each table side has eight columns", () => {
    renderAt(fixtureSlice());
    const grid = (name: string) => must(card(name).parentElement?.parentElement);
    expect(grid(COVER).className).toContain("grid-cols-1");
    expect(grid(PATHS)).toBe(grid(COVER));
    expect(grid(COVER).className).not.toContain("auto-fit");
  });
});

describe("Forecast page: cash flow in FY26", () => {
  it("draws the base walk, then the downside walk when that case is chosen", () => {
    renderAt(fixtureSlice());
    expect(labels(WALK)).toEqual(WALK_BASE);
    choose("Downside case");
    expect(labels(WALK)).toEqual(WALK_DOWN);
  });

  it("draws the missing Other step as n.a. with no column, in both cases", () => {
    renderAt(fixtureSlice());
    const drawn = () =>
      [...figure(WALK).querySelectorAll(".recharts-wrapper [data-bar]")].map((b) =>
        b.getAttribute("data-step"),
      );
    for (const _case of ["Base case", "Downside case"]) {
      choose(_case);
      expect(
        [...figure(WALK).querySelectorAll("[data-missing]")].map((m) => m.textContent),
      ).toEqual(["n.a."]);
      expect(drawn()).toEqual([
        "EBITDA",
        "Interest",
        "Tax",
        "Working capital",
        "Capex",
        "Free cash flow",
      ]);
    }
  });

  it("draws the legend words and the subtitle and basis line", () => {
    renderAt(fixtureSlice());
    expect(
      within(within(figure(WALK)).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Total", "Cash out (minus)", "Cash in (plus)"]);
    expect(within(figure(WALK)).getByText("FY26, USD millions")).toBeInTheDocument();
    expect(
      within(figure(WALK)).getByText(
        "Other cash items were not forecast: the slot stays empty and is not counted as zero.",
      ),
    ).toBeInTheDocument();
  });

  it("holds both cases in the table, n.a. for Other in both", () => {
    renderAt(fixtureSlice());
    expect(tableRows(WALK)).toEqual(WALK_TABLE.map((r) => [...r]));
    expect(
      within(figure(WALK))
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["FY26, USD millions", "Base case", "Downside case"]);
  });

  it("sets the walk and the side column in the auto-fit grid, the table side having three columns", () => {
    renderAt(fixtureSlice());
    const grid = must(card(WALK).parentElement?.parentElement);
    expect(grid.className).toContain("auto-fit");
    expect(grid.className).not.toContain("grid-cols-1");
  });

  it("draws the gap panel beside the walk, with the title and the reason", () => {
    renderAt(fixtureSlice());
    expect(screen.getByText("Not established for this run")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Quarterly cash flow. The sources give annual figures only, so no quarter-by-quarter path was built.",
      ),
    ).toBeInTheDocument();
  });

  it("draws what would change the forecast as a note with its trace control", () => {
    renderAt(fixtureSlice());
    const note = screen.getByRole("region", { name: WATCH });
    expect(
      within(note).getByText(
        "A second debt-funded dividend of the size paid in 2024 would add about a turn of leverage in either case and remove the cash build the base case relies on.",
      ),
    ).toBeInTheDocument();
    expect(
      within(note).getByRole("link", { name: `Show the sources for ${WATCH}` }),
    ).toHaveAttribute("href", ADDRESS);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("draws the limitations item as a link to the limitations page with its sentence", () => {
    renderAt(fixtureSlice());
    const link = screen.getByRole("link", { name: /Limitations of the forecast/ });
    expect(link).toHaveAttribute("href", `${BASE}/limitations`);
    expect(link).toHaveTextContent(
      "Limitations of the forecastSix qualifications apply, two of them to the downside case.",
    );
  });
});

describe("Forecast page: sources, tables and states", () => {
  it("gives every trace control its own name and the address only as href", () => {
    const { container } = renderAt(fixtureSlice());
    const links = screen.getAllByRole("link", { name: /^Show the sources for / });
    expect(links.map((l) => l.getAttribute("aria-label"))).toEqual([
      "Show the sources for Base case",
      "Show the sources for Downside case",
      `Show the sources for ${DRIVERS}`,
      `Show the sources for ${COVER}`,
      `Show the sources for ${PATHS}`,
      `Show the sources for ${WALK}`,
      `Show the sources for ${WATCH}`,
    ]);
    for (const link of links) expect(link).toHaveAttribute("href", ADDRESS);
    for (const el of Array.from(container.querySelectorAll("[title], [aria-label]"))) {
      expect(`${el.getAttribute("title") ?? ""}${el.getAttribute("aria-label") ?? ""}`).not.toMatch(
        /#\/|evidence|\.json|\.pdf/i,
      );
    }
    expect(container.textContent).not.toContain(ADDRESS);
  });

  it("draws no trace control where the slice gives no address", () => {
    renderAt(edited([...F, "watch", "trace"], null));
    expect(screen.queryByRole("link", { name: `Show the sources for ${WATCH}` })).toBeNull();
    expect(screen.getByRole("link", { name: `Show the sources for ${WALK}` })).toBeInTheDocument();
  });

  it("puts no table on the canvas: every table is inside a card, and none shows until chosen", () => {
    renderAt(fixtureSlice());
    expect(document.querySelectorAll("table")).toHaveLength(0);
    for (const title of [DRIVERS, COVER, PATHS, WALK]) {
      fireEvent.click(within(figure(title)).getByRole("radio", { name: "Table" }));
      expect(card(title).querySelector("table")).not.toBeNull();
    }
    expect(document.querySelectorAll("table")).toHaveLength(4);
  });

  it("draws the not found state for an issuer or run the slice does not hold", () => {
    renderAt(fixtureSlice(), "nobody");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole("radiogroup")).toBeNull();
  });

  it.each([
    ["a tab", [...F, "tabs", 0, "href"], 1, "tabs[0].href: expected a string"],
    [
      "a driver row",
      [...F, "drivers", "rows", 0, "axis", "min"],
      "0",
      "drivers.rows[0].axis.min: expected a number",
    ],
    [
      "an interest cover point",
      [...F, "interestCover", "cases", 0, "values", 0],
      "2.6",
      "interestCover.cases[0].values[0]: expected a number",
    ],
    [
      "an EBITDA label",
      [...F, "ebitda", "series", 0, "labels", 0],
      1,
      "ebitda.series[0].labels[0]: expected a string or null",
    ],
    [
      "a walk step",
      [...F, "walk", "caseSteps", 0, 0, "to"],
      "5080",
      "walk.caseSteps[0][0].to: expected a number",
    ],
    ["the gap", [...F, "gap", "reason"], 1, "gap.reason: expected a string"],
    ["the note", [...F, "watch", "text"], 1, "watch.text: expected a string"],
    [
      "the limitations item",
      [...F, "limitations", "href"],
      1,
      "limitations.href: expected a string",
    ],
  ] as const)(
    "leaves an invalid slice with %s to the app, naming the failing path",
    (_n, steps, value, reason) => {
      renderAt(edited(steps, value));
      expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
      expect(screen.getByText(`runs[0].forecast.${reason}`)).toBeInTheDocument();
    },
  );
});
