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

function renderAt(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/forecast`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

const figure = (name: string): HTMLElement => screen.getByRole("figure", { name });
const choose = (name: string) => {
  fireEvent.click(screen.getByRole("radio", { name }));
};
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

describe("Forecast page: sources, tables and states", () => {
  it("draws no trace control where the slice gives no address", () => {
    renderAt(edited([...F, "watch", "trace"], null));
    expect(screen.queryByRole("link", { name: `Show the sources for ${WATCH}` })).toBeNull();
    expect(screen.getByRole("link", { name: `Show the sources for ${WALK}` })).toBeInTheDocument();
  });
});
