import { fireEvent, render, screen, within } from "@testing-library/react";
import { ComparisonChart, type ComparisonPanel } from "./ComparisonChart";

// Values and strings are copied from the mock's script block (Model 3 Model, "The two cases side by
// side"): each panel's max is the larger of its two values, as the mock's own widths use.
const PANELS: ComparisonPanel[] = [
  {
    measure: "Revenue, USD millions",
    max: 10190,
    values: [10190, 9050],
    texts: ["10,190", "9,050"],
  },
  {
    measure: "EBITDA as defined, USD millions",
    max: 5460,
    values: [5460, 4350],
    texts: ["5,460", "4,350"],
  },
  {
    measure: "Free cash flow, USD millions",
    max: 2836,
    values: [2836, 1870],
    texts: ["2,836", "1,870"],
  },
  { measure: "Net leverage, times", max: 5.2, values: [3.8, 5.2], texts: ["3.8x", "5.2x"] },
  { measure: "Interest cover, times", max: 3.6, values: [3.6, 2.4], texts: ["3.6x", "2.4x"] },
  {
    measure: "Lowest cash balance, USD millions",
    max: 2790,
    values: [2790, null],
    texts: ["2,790", null],
  },
];
const TABLE = {
  head: ["FY27", "Base case", "Downside case"],
  rows: [
    { label: "Revenue, USD millions", cells: ["10,190", "9,050"] },
    { label: "EBITDA as defined, USD millions", cells: ["5,460", "4,350"] },
    { label: "Free cash flow, USD millions", cells: ["2,836", "1,870"] },
    { label: "Net leverage", cells: ["3.8x", "5.2x"] },
    { label: "Interest cover", cells: ["3.6x", "2.4x"] },
    { label: "Lowest cash balance, USD millions", cells: ["2,790", null] },
  ],
};
const CASES: [string, string] = ["Base case", "Downside case"];

function renderCmp() {
  return render(
    <ComparisonChart
      title="The two cases side by side"
      subtitle="FY27, each measure on its own scale"
      cases={CASES}
      rowLabels={["Base", "Downside"]}
      panels={PANELS}
      table={TABLE}
    />,
  );
}

function panelOf(name: string) {
  const heading = screen.getByRole("heading", { name });
  const panel = heading.closest("[data-panel]");
  if (!(panel instanceof HTMLElement)) throw new Error(`no panel for ${name}`);
  return panel;
}

describe("ComparisonChart chart side", () => {
  it("draws six panels, each headed by its measure", () => {
    const { container } = renderCmp();
    expect(container.querySelectorAll("[data-panel]")).toHaveLength(6);
    expect([...container.querySelectorAll("[data-panel] h5")].map((h) => h.textContent)).toEqual(
      PANELS.map((p) => p.measure),
    );
  });

  it("draws a bar for each present value and none for the missing one", () => {
    const { container } = renderCmp();
    expect(container.querySelectorAll("[data-bar]")).toHaveLength(11);
    const panel = panelOf("Lowest cash balance, USD millions");
    expect(panel.querySelectorAll("[data-bar]")).toHaveLength(1);
    expect(panel.querySelector('[data-bar][data-case="Downside case"]')).toBeNull();
  });

  it("draws n.a. in the missing slot only", () => {
    const { container } = renderCmp();
    const na = container.querySelectorAll("[data-missing]");
    expect(na).toHaveLength(1);
    expect(na[0]).toHaveTextContent("n.a.");
    expect(panelOf("Lowest cash balance, USD millions").contains(na[0] ?? null)).toBe(true);
  });

  it("sets each width from its value over the panel's own max", () => {
    const { container } = renderCmp();
    const width = (measure: string, c: string) =>
      panelOf(measure).querySelector(`[data-bar][data-case="${c}"]`)?.getAttribute("data-width");
    expect(Number(width("Revenue, USD millions", "Base case"))).toBeCloseTo(100, 5);
    expect(Number(width("Revenue, USD millions", "Downside case"))).toBeCloseTo(
      (9050 / 10190) * 100,
      5,
    );
    expect(Number(width("Net leverage, times", "Base case"))).toBeCloseTo((3.8 / 5.2) * 100, 5);
    expect(Number(width("Net leverage, times", "Downside case"))).toBeCloseTo(100, 5);
    expect(container.querySelectorAll("[data-bar]")[0]?.getAttribute("style")).toContain("width");
  });

  it("shows every value as its exact string", () => {
    renderCmp();
    const texts = (m: string) =>
      [...panelOf(m).querySelectorAll("[data-value]")].map((v) => v.textContent);
    expect(texts("Revenue, USD millions")).toEqual(["10,190", "9,050"]);
    expect(texts("Net leverage, times")).toEqual(["3.8x", "5.2x"]);
    expect(texts("Interest cover, times")).toEqual(["3.6x", "2.4x"]);
    expect(texts("Lowest cash balance, USD millions")).toEqual(["2,790", ""]);
  });

  it("colours the two cases from the series palette", () => {
    const { container } = renderCmp();
    const fill = (c: string) =>
      (container.querySelector(`[data-bar][data-case="${c}"]`) as HTMLElement).style
        .backgroundColor;
    expect(fill("Base case")).toBe("var(--color-chart-1)");
    expect(fill("Downside case")).toBe("var(--color-chart-2)");
  });

  it("rounds each bar by the mock's 6px, lays the row out as 72px / flexible / 56px, and centres the legend", () => {
    const { container } = renderCmp();
    expect(container.querySelector("[data-bar]")).toHaveClass("rounded-ds-xs");
    const grid = container.querySelector("[data-bar]")?.parentElement?.parentElement;
    expect(grid).toHaveClass("grid-cols-[72px_minmax(0,1fr)_56px]");
    expect(screen.getByRole("list", { name: "Legend" })).toHaveClass("justify-center");
  });

  it("labels the rows with the short names and legends the case names", () => {
    renderCmp();
    expect(within(panelOf("Revenue, USD millions")).getByText("Downside")).toBeInTheDocument();
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(
      within(legend)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Base case", "Downside case"]);
  });

  it("adds no focus stop beyond the frame's own Chart or Table toggle", () => {
    const { container } = renderCmp();
    const panels = [...container.querySelectorAll("[data-panel]")];
    expect(panels).toHaveLength(6);
    for (const p of panels) {
      expect(p.querySelectorAll("[tabindex], a, button, input, select, textarea")).toHaveLength(0);
    }
    expect(screen.getByRole("list", { name: "Legend" }).querySelector("[tabindex]")).toBeNull();
    expect(container.querySelector(".recharts-wrapper")).toBeNull();
  });

  it("zero draws a mark, not nothing", () => {
    const zero: ComparisonPanel = { measure: "Z", max: 10, values: [0, 5], texts: ["0", "5"] };
    const { container } = render(
      <ComparisonChart
        title="Z"
        cases={CASES}
        panels={[zero]}
        table={{ head: ["F", ...CASES], rows: [{ label: "Z", cells: ["0", "5"] }] }}
      />,
    );
    const bar = container.querySelector('[data-bar][data-case="Base case"]');
    expect(bar).toHaveAttribute("data-zero");
    expect(bar).toHaveAttribute("data-width", "0");
  });
});

describe("ComparisonChart table side", () => {
  it("shows the mock's strings, n.a. for the missing value", () => {
    renderCmp();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /Lowest cash balance/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent.replace("not available", "")),
    ).toEqual(["2,790", "n.a."]);
  });
});

describe("ComparisonChart check", () => {
  const panel: ComparisonPanel = { measure: "M", max: 10, values: [5, 4], texts: ["5", "4"] };
  const table = { head: ["F", ...CASES], rows: [{ label: "M", cells: ["5", "4"] }] };
  function throwsOn(ui: React.ReactElement, pattern: RegExp) {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(ui)).toThrow(pattern);
    quiet.mockRestore();
  }
  const make = (panels: ComparisonPanel[], t = table) => (
    <ComparisonChart title="T" cases={CASES} panels={panels} table={t} />
  );
  it("throws when a present value has no text", () => {
    throwsOn(make([{ ...panel, texts: [null, "4"] }]), /"M".*text/);
  });
  it("throws when a missing value carries a text", () => {
    throwsOn(make([{ ...panel, values: [5, null] }]), /"M".*missing/);
  });
  it("throws on a negative value, a value above max or a max that is not above zero", () => {
    throwsOn(make([{ ...panel, values: [-1, 4] }]), /"M".*zero or more/);
    throwsOn(make([{ ...panel, values: [11, 4] }]), /"M".*above/);
    throwsOn(make([{ ...panel, max: 0 }]), /"M".*max/);
  });
  it("throws on a repeated measure", () => {
    throwsOn(
      make([panel, panel], {
        ...table,
        rows: [...table.rows, ...table.rows],
      }),
      /distinct/,
    );
  });
  it("throws when the table columns are not the cases", () => {
    throwsOn(make([panel], { ...table, head: ["F", "A", "B"] }), /cases/);
  });
  it("throws when the table has a different number of rows", () => {
    throwsOn(make([panel], { ...table, rows: [] }), /one row per panel/);
  });
  it("throws when a table cell differs from the panel's text", () => {
    throwsOn(make([panel], { ...table, rows: [{ label: "M", cells: ["5", "9"] }] }), /"M".*cell/);
  });
});
