import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { edited, fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";
const F = ["runs", 0, "portfolioFit"] as const;
const LIMITS = "Exposure against limits";
const RATINGS = "Agency ratings";
const SCATTER = "Leverage and margin against holdings";
const STRIPS = "Where the issuer sits in the portfolio";

// Everything below is copied from the mock (Model 4 Portfolio fit), not read from the page code.
const LIMIT_TEXTS = [
  ["Single issuer", "2.1%", "limit 3.0%"],
  ["Aerospace and defence", "9.4%", "limit 12.0%"],
  ["Rated single B", "31.0%", "limit 35.0%"],
] as const;
const LIMIT_TABLE = [
  ["Single issuer", "2.1%", "3.0%"],
  ["Aerospace and defence", "9.4%", "12.0%"],
  ["Rated single B", "31.0%", "35.0%"],
  ["United States", "58.0%", "n.a."],
  ["Subordinated debt", "n.a.", "10.0%"],
] as const;
const HOLDINGS = [
  ["A", "3.1x", "22%"],
  ["B", "4.2x", "31%"],
  ["C", "2.6x", "14%"],
  ["D", "5.1x", "27%"],
  ["E", "6.8x", "19%"],
  ["F", "3.8x", "41%"],
  ["G", "4.6x", "9%"],
  ["H", "5.6x", "36%"],
  ["I", "2.4x", "18%"],
] as const;
const STRIP_TABLE = [
  ["Net leverage", "2.4x", "6.8x", "5.9x"],
  ["Interest cover", "1.6x", "6.2x", "2.9x"],
  ["EBITDA margin", "9%", "53%", "53.1%"],
  ["Spread over benchmark", "180 bp", "520 bp", "n.a."],
] as const;

function renderAt(slice: unknown, issuer = "transdigm", run = "2025-06-30") {
  window.location.hash = `#/model/${issuer}/${run}/portfolio-fit`;
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

function figure(title: string): HTMLElement {
  return must(screen.getByRole("heading", { name: title }).closest<HTMLElement>("figure"));
}

/** The text of a cell with the screen-reader words of a missing figure removed. */
const cellText = (c: HTMLElement) => c.textContent.replace("not available", "");

function tableRows(chart: HTMLElement): string[][] {
  fireEvent.click(within(chart).getByRole("radio", { name: "Table" }));
  return within(chart)
    .getAllByRole("row")
    .slice(1)
    .map((r) => [
      ...within(r)
        .getAllByRole("rowheader")
        .map((h) => h.textContent),
      ...within(r).getAllByRole("cell").map(cellText),
    ]);
}

describe("Portfolio fit page", () => {
  it("orders the headings h1 (the issuer), h2 (the sections), h3 (the chart titles)", () => {
    renderAt(fixtureSlice());
    expect(screen.getAllByRole("heading").map((h) => [h.tagName, h.textContent])).toEqual([
      ["H1", "TransDigm Group"],
      ["H2", "Portfolio fit"],
      ["H3", LIMITS],
      ["H3", RATINGS],
      ["H3", "Relative value"],
      ["H3", SCATTER],
      ["H3", STRIPS],
    ]);
  });

  it("takes the hidden h2 from the tab label, so the two cannot differ", () => {
    renderAt(fixtureSlice());
    const tab = within(screen.getByRole("navigation", { name: "Pages" })).getByRole("link", {
      name: "Portfolio fit",
    });
    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe(tab.textContent);
  });

  it("draws positions from the mock's data", () => {
    const { container } = renderAt(fixtureSlice());
    const single = must(container.querySelector<HTMLElement>('[data-column="Single issuer"]'));
    expect(Number(single.querySelector("[data-bar]")?.getAttribute("data-height"))).toBeCloseTo(
      56,
      5,
    );
    expect(Number(single.querySelector("[data-tick]")?.getAttribute("data-at"))).toBeCloseTo(80, 5);
    const us = must(container.querySelector<HTMLElement>('[data-column="United States"]'));
    expect(us.querySelector("[data-limit-at]")?.getAttribute("data-limit-at")).toBe("86");
    const row = must(figure(STRIPS).querySelector<HTMLElement>("[data-row]"));
    expect(Number(row.querySelector("[data-range]")?.getAttribute("data-left"))).toBeCloseTo(30, 5);
    expect(Number(row.querySelector("[data-range]")?.getAttribute("data-width"))).toBeCloseTo(
      55,
      5,
    );
    expect(Number(row.querySelector("[data-marker]")?.getAttribute("data-left"))).toBeCloseTo(
      73.75,
      5,
    );
    expect(figure(STRIPS).querySelectorAll("[data-value] i")).toHaveLength(0);
    // Scatter: TransDigm at 5.9x on a 2x to 8x axis, and above Holding F (53.1% against 41%).
    const axis = must(
      figure(SCATTER).querySelector(".recharts-xAxis .recharts-cartesian-axis-line"),
    );
    const [x1, x2] = [Number(axis.getAttribute("x1")), Number(axis.getAttribute("x2"))];
    const mark = (name: string) => must(figure(SCATTER).querySelector(`[data-point="${name}"]`));
    const me = must(mark("TransDigm").querySelector("circle"));
    expect(Number(me.getAttribute("cx"))).toBeCloseTo(x1 + ((5.9 - 2) / 6) * (x2 - x1), 3);
    const f = must(mark("Holding F").querySelector("rect"));
    expect(Number(me.getAttribute("cy"))).toBeLessThan(Number(f.getAttribute("y")));
  });

  it("marks the Portfolio fit tab current", () => {
    renderAt(fixtureSlice());
    const tabs = within(screen.getByRole("navigation", { name: "Pages" }));
    expect(tabs.getByRole("link", { name: "Portfolio fit" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("draws the limit columns, a bar and a dashed tick each, with the two missing rules", () => {
    renderAt(fixtureSlice());
    const chart = figure(LIMITS);
    expect(
      within(chart).getByText(
        "Share of the portfolio after the proposed position; each limit on its own scale",
      ),
    ).toBeInTheDocument();
    expect(
      within(chart).getByText(
        "No country limit is set (limit n.a.). Exposure to subordinated debt was not measured, so no bar is drawn.",
      ),
    ).toBeInTheDocument();
    for (const [label, exposure, limit] of LIMIT_TEXTS) {
      const column = must(chart.querySelector<HTMLElement>(`[data-column="${label}"]`));
      expect(column.querySelector("[data-exposure]")?.textContent).toBe(exposure);
      expect(column.querySelector("[data-tick]")?.textContent).toBe(limit);
    }
    const us = must(chart.querySelector<HTMLElement>('[data-column="United States"]'));
    expect(us.querySelector("[data-exposure]")?.textContent).toBe("58.0%");
    expect(us.querySelector("[data-tick]")).toBeNull();
    expect(cellText(must(us.querySelector<HTMLElement>("[data-limit-missing]")))).toBe(
      "limit n.a.",
    );
    const sub = must(chart.querySelector<HTMLElement>('[data-column="Subordinated debt"]'));
    expect(sub.querySelector("[data-bar]")).toBeNull();
    expect(cellText(must(sub.querySelector<HTMLElement>("[data-missing]")))).toBe("n.a.");
    expect(sub.querySelector("[data-tick]")?.textContent).toBe("limit 10.0%");
    expect(chart.querySelectorAll("[data-bar]")).toHaveLength(4);
    expect(chart.querySelectorAll("[data-tick]")).toHaveLength(4);
  });

  it("draws the limits table with n.a. for the missing exposure and the missing limit", () => {
    renderAt(fixtureSlice());
    const chart = figure(LIMITS);
    expect(tableRows(chart)).toEqual(LIMIT_TABLE.map((r) => [...r]));
    expect(
      within(chart)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Limit", "Exposure", "Limit"]);
  });

  it("draws the two agency ratings as tiles with the outlook line under each", () => {
    renderAt(fixtureSlice());
    const section = must(
      screen.getByRole("heading", { name: RATINGS }).closest<HTMLElement>("section"),
    );
    const tiles = within(section).getAllByRole("article");
    expect(tiles.map((t) => t.textContent)).toEqual([
      "Moody's, corporate familyB1",
      "S&P, issuer creditB+",
    ]);
    expect(within(section).getAllByText("Stable outlook")).toHaveLength(2);
    expect(
      within(section).getByRole("link", { name: "Show the sources for Agency ratings" }),
    ).toHaveAttribute("href", ADDRESS);
  });

  it("draws a rating that is missing as n.a. and leaves out its outlook line", () => {
    renderAt(
      edited([...F, "ratings", "tiles", 1], {
        label: "S&P, issuer credit",
        value: null,
        caption: null,
      }),
    );
    const tiles = screen.getAllByRole("article");
    expect(cellText(must(tiles[1]))).toBe("S&P, issuer creditn.a.");
    expect(screen.getAllByText("Stable outlook")).toHaveLength(1);
  });

  it("draws the failed relative value part as Not assessable with its sentence and no chart", () => {
    renderAt(fixtureSlice());
    const section = must(
      screen.getByRole("heading", { name: "Relative value" }).closest<HTMLElement>("section"),
    );
    expect(within(section).getByText("Spread against holdings")).toBeInTheDocument();
    expect(within(section).getByText("Not assessable")).toBeInTheDocument();
    expect(
      within(section).getByText(
        "The pricing comparison failed in this run, so the spread paid for this risk could not be set against the rest of the portfolio.",
      ),
    ).toBeInTheDocument();
    expect(section.querySelector("figure, svg[role=img], table, [data-bar]")).toBeNull();
    expect(within(section).queryByRole("link")).toBeNull();
  });

  it("draws the scatter with its legend, the two holdings not plotted and the basis line", () => {
    renderAt(fixtureSlice());
    const chart = figure(SCATTER);
    expect(
      within(chart).getByText("Latest twelve months, one mark per issuer held"),
    ).toBeInTheDocument();
    expect(
      within(chart).getByText("Holdings are shown without names in this sample."),
    ).toBeInTheDocument();
    expect(
      within(chart).getByText(
        "Not plotted: Holding J (EBITDA margin n.a.), Holding K (net leverage n.a.).",
      ),
    ).toBeInTheDocument();
    expect(
      within(within(chart).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["TransDigm", "Other holdings"]);
  });

  it("draws the scatter table: the issuer, holdings A to I, then J and K with n.a.", () => {
    renderAt(fixtureSlice());
    expect(tableRows(figure(SCATTER))).toEqual([
      ["TransDigm", "5.9x", "53.1%"],
      ...HOLDINGS.map(([name, x, y]) => [`Holding ${name}`, x, y]),
      ["Holding J", "4.4x", "n.a."],
      ["Holding K", "n.a.", "24%"],
    ]);
    expect(
      within(figure(SCATTER))
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Issuer", "Net leverage", "EBITDA margin"]);
  });

  it("draws one strip per measure, an issuer tick on three, and the missing spread as n.a.", () => {
    renderAt(fixtureSlice());
    const chart = figure(STRIPS);
    expect(
      within(chart).getByText("The issuer against the range across holdings"),
    ).toBeInTheDocument();
    expect(
      within(chart).getByText(
        "The issuer has the highest margin held and sits near the top of the leverage range. Its spread is missing because the pricing comparison failed.",
      ),
    ).toBeInTheDocument();
    for (const text of [
      "Holdings: 2.4x to 6.8x",
      "Holdings: 1.6x to 6.2x",
      "Holdings: 9% to 53%",
      "Holdings: 180 to 520 basis points",
      "5.9x",
      "2.9x",
      "53.1%",
    ]) {
      expect(within(chart).getByText(text)).toBeInTheDocument();
    }
    expect(chart.querySelectorAll("[data-range]")).toHaveLength(4);
    expect(chart.querySelectorAll("[data-marker]")).toHaveLength(3);
    const spread = must(
      within(chart).getByText("Spread over benchmark").closest<HTMLElement>("[data-row]"),
    );
    expect(spread.querySelector("[data-range]")).not.toBeNull();
    expect(spread.querySelector("[data-marker]")).toBeNull();
    expect(cellText(must(spread.querySelector<HTMLElement>("[data-missing]")))).toBe("n.a.");
    expect(
      within(within(chart).getByRole("list", { name: "Legend" }))
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Range across holdings", "TransDigm"]);
  });

  it("draws the strips table with n.a. for the missing spread", () => {
    renderAt(fixtureSlice());
    const chart = figure(STRIPS);
    expect(tableRows(chart)).toEqual(STRIP_TABLE.map((r) => [...r]));
    expect(
      within(chart)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Measure", "Lowest held", "Highest held", "TransDigm"]);
  });

  it("keeps every table inside a card and puts none on the canvas", () => {
    renderAt(fixtureSlice());
    for (const title of [LIMITS, SCATTER, STRIPS]) {
      const chart = figure(title);
      fireEvent.click(within(chart).getByRole("radio", { name: "Table" }));
      const card = chart.closest(".rounded-ds-lg");
      expect(card?.querySelector("table")).not.toBeNull();
    }
    expect(document.querySelectorAll("table")).toHaveLength(3);
  });

  it("sets the half-width charts in the auto-fit grid, and a table of five columns on a whole row", () => {
    const { unmount } = renderAt(fixtureSlice());
    const grid = (title: string) => must(figure(title).closest(".rounded-ds-lg")).parentElement;
    for (const title of [LIMITS, SCATTER, STRIPS]) {
      expect(grid(title)?.parentElement?.className).toContain("auto-fit");
    }
    unmount();
    const head = ["Measure", "Lowest held", "Highest held", "Cases", "TransDigm"];
    const slice = edited([...F, "strips", "head"], head) as {
      runs: { portfolioFit: { strips: { rows: { cells: unknown[] }[] } } }[];
    };
    // The cells end with the marker's text, so the extra column sits before it.
    for (const row of must(slice.runs[0]).portfolioFit.strips.rows) row.cells.splice(2, 0, "x");
    renderAt(slice);
    const wide = must(figure(STRIPS).closest(".rounded-ds-lg")).parentElement?.parentElement;
    expect(wide?.className).toContain("grid-cols-1");
  });

  it("gives each chart and the ratings one trace control named by its title", () => {
    renderAt(fixtureSlice());
    const names = screen
      .getAllByRole("link", { name: /^Show the sources for / })
      .map((l) => l.getAttribute("aria-label"));
    expect(names).toEqual([
      `Show the sources for ${LIMITS}`,
      `Show the sources for ${RATINGS}`,
      `Show the sources for ${SCATTER}`,
      `Show the sources for ${STRIPS}`,
    ]);
    for (const link of screen.getAllByRole("link", { name: /^Show the sources for / })) {
      expect(link).toHaveAttribute("href", ADDRESS);
    }
  });

  it("draws no trace control where the slice gives no address", () => {
    renderAt(edited([...F, "limits", "trace"], null));
    expect(screen.queryByRole("link", { name: `Show the sources for ${LIMITS}` })).toBeNull();
    expect(
      screen.getByRole("link", { name: `Show the sources for ${RATINGS}` }),
    ).toBeInTheDocument();
  });

  it("puts the trace addresses only in href, never in text, title or aria-label", () => {
    const { container } = renderAt(fixtureSlice());
    for (const el of Array.from(container.querySelectorAll("[title], [aria-label]"))) {
      expect(`${el.getAttribute("title") ?? ""}${el.getAttribute("aria-label") ?? ""}`).not.toMatch(
        /#\/|evidence|\.json|\.pdf/i,
      );
    }
    expect(container.textContent).not.toContain(ADDRESS);
  });

  it("names no company but the issuer: the holdings stay letters", () => {
    const { container } = renderAt(fixtureSlice());
    fireEvent.click(within(figure(SCATTER)).getByRole("radio", { name: "Table" }));
    const names = within(figure(SCATTER))
      .getAllByRole("rowheader")
      .map((h) => h.textContent);
    expect(names.slice(1, 10)).toEqual("ABCDEFGHI".split("").map((l) => `Holding ${l}`));
    expect(container.textContent).not.toMatch(/\b(Inc|Corp|Ltd|plc)\b/);
  });

  it("draws the not found state for an issuer or run the slice does not hold", () => {
    renderAt(fixtureSlice(), "nobody");
    expect(screen.getByText("Not found for this run")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it.each([
    [
      "a limit column",
      [...F, "limits", "columns", 0, "scaleMax"],
      "x",
      "limits.columns[0].scaleMax: expected a number",
    ],
    [
      "a rating tile",
      [...F, "ratings", "tiles", 0, "value"],
      1,
      "ratings.tiles[0].value: expected a string or null",
    ],
    [
      "the relative value part",
      [...F, "relativeValue", "reason"],
      1,
      "relativeValue.reason: expected a string",
    ],
    [
      "a scatter point",
      [...F, "scatter", "points", 0, "x"],
      "5.9",
      "scatter.points[0].x: expected a number",
    ],
    [
      "a strip row",
      [...F, "strips", "rows", 0, "axis", "min"],
      "0",
      "strips.rows[0].axis.min: expected a number",
    ],
  ] as const)(
    "leaves an invalid slice with %s to the app, naming the failing path",
    (_n, steps, value, reason) => {
      renderAt(edited(steps, value));
      expect(screen.getByText("This part of the library could not be read")).toBeInTheDocument();
      expect(screen.getByText(`runs[0].portfolioFit.${reason}`)).toBeInTheDocument();
    },
  );
});
