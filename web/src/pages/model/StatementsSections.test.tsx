import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "@/App";
import type { LoadResult } from "@/data";
import { fixtureSlice, must } from "./slice/test-fixture";

const ADDRESS = "#/library/transdigm/2025-06-30/evidence";

function renderAt(slice: unknown) {
  window.location.hash = "#/model/transdigm/2025-06-30/statements";
  const result: LoadResult = {
    kind: "ok",
    data: { schema: "credit-os-data/1", issuers: [], model: slice },
  };
  return render(<App result={result} />);
}

/** The fixture's first run's statements member, to edit in a test-only slice. */
function draft(): { slice: unknown; page: Record<string, unknown> } {
  const slice = fixtureSlice() as { runs: { statements: Record<string, unknown> }[] };
  return { slice, page: must(slice.runs[0]).statements };
}

const figure = (name: string): HTMLElement => screen.getByRole("figure", { name });
const showTable = (name: string) => {
  fireEvent.click(within(figure(name)).getByRole("radio", { name: "Table" }));
};
const choose = (name: string) => {
  fireEvent.click(screen.getByRole("radio", { name }));
};
const marks = (name: string, attribute: string): string[] =>
  [...figure(name).querySelectorAll(`.recharts-wrapper [${attribute}]`)].map(
    (el) => el.textContent,
  );
const stepsDrawn = (name: string): string[] =>
  [...figure(name).querySelectorAll(".recharts-wrapper [data-bar]")].map(
    (el) => el.getAttribute("data-step") ?? "",
  );
/**
 * The body rows of the figure's table, each as its label then its figure cells' text (the last
 * cell holds the trace control). A missing cell reads as its visible "n.a.", not its hidden words.
 */
const rowsOf = (name: string): string[][] =>
  within(within(figure(name)).getByRole("table"))
    .getAllByRole("row")
    .slice(1)
    .map((row) => [
      must(within(row).getByRole("rowheader").textContent),
      ...within(row)
        .getAllByRole("cell")
        .slice(0, -1)
        .map((c) => c.textContent.replace("not available", "")),
    ]);

describe("Model page: bridges", () => {
  it("draws each bridge with its subtitle, basis note and legend words", () => {
    renderAt(fixtureSlice());
    const walk = figure("EBITDA bridge");
    expect(within(walk).getByText("FY24 to FY25E, USD millions")).toBeInTheDocument();
    expect(
      within(walk).getByText("Costs include the first full year of the 2024 acquisitions."),
    ).toBeInTheDocument();
    expect(
      within(walk)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Total", "Increase (plus)", "Decrease (minus)"]);
    expect(
      within(figure("Net debt walk")).getByText(
        "Acquisitions are assumed at zero (0). Shareholder returns were not forecast (n.a.) and are not counted as zero.",
      ),
    ).toBeInTheDocument();
  });

  it("follows the chosen case: the base walk, then the downside walk", () => {
    renderAt(fixtureSlice());
    expect(marks("EBITDA bridge", "data-label")).toEqual([
      "4,173",
      "+330",
      "+290",
      "+120",
      "-223",
      "4,690",
    ]);
    expect(marks("Net debt walk", "data-label")).toEqual([
      "26,300",
      "-2,540",
      "-2,836",
      "0",
      "20,924",
    ]);
    choose("Downside case");
    expect(marks("EBITDA bridge", "data-label")).toEqual([
      "4,173",
      "+150",
      "+180",
      "+120",
      "-63",
      "4,560",
    ]);
    expect(marks("Net debt walk", "data-label")).toEqual([
      "26,320",
      "-1,810",
      "-1,870",
      "0",
      "22,640",
    ]);
  });

  it("draws the missing step as n.a. with no column, and a zero step as 0 with a hairline", () => {
    renderAt(fixtureSlice());
    expect(marks("Net debt walk", "data-missing")).toEqual(["n.a."]);
    expect(stepsDrawn("Net debt walk")).not.toContain("Shareholder returns");
    expect(stepsDrawn("Net debt walk")).toEqual([
      "FY25E",
      "Cash flow FY26",
      "Cash flow FY27",
      "Acquisitions",
      "FY27E",
    ]);
    const zero = figure("Net debt walk").querySelector(".recharts-wrapper [data-zero]");
    expect(zero?.getAttribute("data-step")).toBe("Acquisitions");
    expect(marks("EBITDA bridge", "data-missing")).toEqual([]);
  });

  it("holds both cases in each table, with n.a. for the missing step", () => {
    renderAt(fixtureSlice());
    showTable("EBITDA bridge");
    expect(rowsOf("EBITDA bridge")).toEqual([
      ["EBITDA as defined, FY24", "4,173", "4,173"],
      ["Volume", "330", "150"],
      ["Price", "290", "180"],
      ["Acquisitions", "120", "120"],
      ["Costs", "-223", "-63"],
      ["EBITDA as defined, FY25E", "4,690", "4,560"],
    ]);
    showTable("Net debt walk");
    const rows = rowsOf("Net debt walk");
    expect(rows[4]).toEqual(["Shareholder returns", "n.a.", "n.a."]);
    expect(rows[3]).toEqual(["Acquisitions", "0", "0"]);
    const heads = within(figure("Net debt walk")).getAllByRole("columnheader");
    expect(heads.slice(0, 3).map((h) => h.textContent)).toEqual([
      "USD millions",
      "Base case",
      "Downside case",
    ]);
  });

  it("gives the chart and every table row its own trace control, named by what it traces", () => {
    renderAt(fixtureSlice());
    const walk = figure("Net debt walk");
    expect(
      within(walk).getByRole("link", { name: "Show the sources for Net debt walk" }),
    ).toHaveAttribute("href", ADDRESS);
    showTable("Net debt walk");
    const links = within(within(walk).getByRole("table")).getAllByRole("link");
    expect(links.map((l) => l.getAttribute("aria-label"))).toEqual(
      [
        "Net debt, FY25E",
        "Free cash flow, FY26",
        "Free cash flow, FY27",
        "Acquisitions",
        "Shareholder returns",
        "Net debt, FY27E",
      ].map((label) => `Show the sources for ${label} (Net debt walk)`),
    );
    for (const link of links) expect(link).toHaveAttribute("href", ADDRESS);
  });

  it("draws no row control where the slice gives no address, and keeps the others", () => {
    const { slice, page } = draft();
    const bridge = (page["bridges"] as { rows: { trace: string | null }[] }[])[0];
    must(must(bridge).rows[1]).trace = null;
    renderAt(slice);
    showTable("EBITDA bridge");
    const links = within(within(figure("EBITDA bridge")).getByRole("table")).getAllByRole("link");
    expect(links).toHaveLength(5);
    expect(links.map((l) => l.getAttribute("aria-label"))).not.toContain(
      "Show the sources for Volume (EBITDA bridge)",
    );
  });
});

describe("Model page: the two cases side by side", () => {
  it("draws six panels with a bar and the exact text for each case, FY27", () => {
    renderAt(fixtureSlice());
    const chart = figure("The two cases side by side");
    expect(within(chart).getByText("FY27, each measure on its own scale")).toBeInTheDocument();
    const panels = [...chart.querySelectorAll("[data-panel]")];
    expect(panels).toHaveLength(6);
    const values = (panel: Element) =>
      [...panel.querySelectorAll("[data-value]")].map((v) => v.textContent);
    expect(panels.map(values)).toEqual([
      ["10,190", "9,050"],
      ["5,460", "4,350"],
      ["2,836", "1,870"],
      ["3.8x", "5.2x"],
      ["3.6x", "2.4x"],
      ["2,790", ""],
    ]);
    expect(
      within(chart)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Base case", "Downside case"]);
  });

  it("draws the missing downside cash balance as n.a. with no bar", () => {
    renderAt(fixtureSlice());
    const chart = figure("The two cases side by side");
    const last = must([...chart.querySelectorAll("[data-panel]")][5]);
    expect(last.querySelectorAll("[data-bar]")).toHaveLength(1);
    expect(last.querySelector("[data-missing]")).toHaveTextContent("n.a.");
    expect(chart.querySelectorAll("[data-missing]")).toHaveLength(1);
    expect(
      within(chart).getByText(
        "Lowest cash balance was not worked out for the downside case because the revolver terms are withheld.",
      ),
    ).toBeInTheDocument();
  });

  it("holds the same strings in its table, with a control for each row", () => {
    renderAt(fixtureSlice());
    showTable("The two cases side by side");
    const rows = rowsOf("The two cases side by side");
    expect(rows).toEqual([
      ["Revenue, USD millions", "10,190", "9,050"],
      ["EBITDA as defined, USD millions", "5,460", "4,350"],
      ["Free cash flow, USD millions", "2,836", "1,870"],
      ["Net leverage", "3.8x", "5.2x"],
      ["Interest cover", "3.6x", "2.4x"],
      ["Lowest cash balance, USD millions", "2,790", "n.a."],
    ]);
    const chart = figure("The two cases side by side");
    expect(within(chart).getAllByRole("link")).toHaveLength(7);
    expect(
      within(chart).getByRole("link", {
        name: "Show the sources for Lowest cash balance, USD millions (The two cases side by side)",
      }),
    ).toHaveAttribute("href", ADDRESS);
    expect(
      within(within(chart).getByRole("table"))
        .getAllByRole("columnheader")
        .slice(0, 3)
        .map((h) => h.textContent),
    ).toEqual(["FY27", "Base case", "Downside case"]);
  });
});

describe("Model page: debt and recovery", () => {
  it("draws debt by instrument ranked, with amount and share", () => {
    renderAt(fixtureSlice());
    const chart = figure("Debt by instrument");
    expect(within(chart).getByText("30 June 2025, USD 29,700 million in all")).toBeInTheDocument();
    expect(
      within(chart)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual([
      "Term loans11,30038%",
      "Senior secured notes10,45035%",
      "Senior subordinated notes7,30025%",
      "Receivables facility6502%",
    ]);
    expect(
      within(chart).getByText(
        "Ranked by size. Term loans and secured notes share the same security.",
      ),
    ).toBeInTheDocument();
    showTable("Debt by instrument");
    expect(rowsOf("Debt by instrument")).toEqual([
      ["Term loans", "11,300", "38%"],
      ["Senior secured notes", "10,450", "35%"],
      ["Senior subordinated notes", "7,300", "25%"],
      ["Receivables facility", "650", "2%"],
    ]);
  });

  it("draws maturities with n.a. for the loans in 2026 and 0 for the notes", () => {
    renderAt(fixtureSlice());
    const chart = figure("Maturities by year");
    expect(within(chart).getByText("Calendar years, USD millions")).toBeInTheDocument();
    expect(marks("Maturities by year", "data-missing")).toEqual(["n.a."]);
    expect(
      chart.querySelector(".recharts-wrapper [data-missing]")?.getAttribute("data-group"),
    ).toBe("2026");
    expect(chart.querySelectorAll(".recharts-wrapper [data-zero]")).toHaveLength(7);
    expect(chart.querySelectorAll(".recharts-wrapper [data-bar]")).toHaveLength(17);
    showTable("Maturities by year");
    const rows = rowsOf("Maturities by year");
    expect(rows[0]).toEqual(["2026", "n.a.", "0", "0"]);
    expect(rows[5]).toEqual(["2031 on", "3,200", "4,150", "4,100"]);
    expect(
      within(chart).getByText(
        "Nothing falls due in 2026 on the notes (0). Loan repayments for 2026 were not established (n.a.).",
      ),
    ).toBeInTheDocument();
  });
});
