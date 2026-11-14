import { fireEvent, render, screen, within } from "@testing-library/react";
import { TrendChart } from "./TrendChart";

const PERIODS = ["FY21", "FY22", "FY23", "FY24", "FY25", "FY26"];

function series(name: string, values: (number | null)[]) {
  return { name, values };
}
function table(name: string, cells: (string | null)[]) {
  return { name, cells };
}

const A = [10, 12, 14, 13, 15, 16];
const B: (number | null)[] = [5, 6, null, 8, 9, 10];
const A_CELLS = ["10.0", "12.0", "14.0", "13.0", "15.0", "16.0"];
const B_CELLS = ["5.0", "6.0", null, "8.0", "9.0", "10.0"];

function renderTwo() {
  return render(
    <TrendChart
      title="Leverage"
      periods={PERIODS}
      series={[series("Net debt", A), series("Gross debt", B)]}
      table={[table("Net debt", A_CELLS), table("Gross debt", B_CELLS)]}
    />,
  );
}

function markers(container: HTMLElement, colour: string): number {
  return [...container.querySelectorAll(".recharts-wrapper [data-marker]")].filter(
    (el) => el.getAttribute("data-series") === colour,
  ).length;
}

describe("TrendChart chart side", () => {
  it("names the plot surface with the chart title and draws the focus token ring", () => {
    const { container } = renderTwo();
    expect(screen.getByRole("application", { name: "Leverage" })).toBeInTheDocument();
    const wrapper = container.querySelector(".recharts-responsive-container")?.parentElement;
    for (const cls of [
      "[&_.recharts-surface:focus-visible]:outline-2",
      "[&_.recharts-surface:focus-visible]:outline-solid",
      "[&_.recharts-surface:focus-visible]:outline-offset-2",
      "[&_.recharts-surface:focus-visible]:outline-focus",
    ]) {
      expect(wrapper).toHaveClass(cls);
    }
  });

  it("throws when two series share a name", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(
        <TrendChart
          title="T"
          periods={["P1", "P2"]}
          series={[series("A", [1, 2]), series("A", [3, 4])]}
          table={[table("A", ["1", "2"]), table("A", ["3", "4"])]}
        />,
      ),
    ).toThrow(/distinct|repeat|duplicate/i);
    quiet.mockRestore();
  });

  it("draws a marker for each present value and none for a null", () => {
    const { container } = renderTwo();
    expect(markers(container, "Net debt")).toBe(6);
    expect(markers(container, "Gross debt")).toBe(5);
  });

  it("breaks the line at a null into two sub-paths and leaves a full line whole", () => {
    const { container } = renderTwo();
    const paths = [...container.querySelectorAll("path.recharts-line-curve")].map(
      (p) => p.getAttribute("d") ?? "",
    );
    expect(paths).toHaveLength(2);
    expect(paths[0]?.match(/M/g)).toHaveLength(1);
    expect(paths[1]?.match(/M/g)).toHaveLength(2);
  });

  it("gives each line its slot's colour and dash, without animation", () => {
    const { container } = renderTwo();
    const paths = [...container.querySelectorAll("path.recharts-line-curve")];
    expect(paths[0]?.getAttribute("stroke")).toBe("var(--color-chart-1)");
    expect(paths[1]?.getAttribute("stroke")).toBe("var(--color-chart-2)");
    expect(paths[1]?.getAttribute("stroke-dasharray")).toBe("6 4");
    expect(paths[0]?.getAttribute("stroke-width")).toBe("2");
  });

  it("puts the periods on the x-axis, oldest first", () => {
    const { container } = renderTwo();
    const ticks = [
      ...container.querySelectorAll(
        ".recharts-xAxis-tick-labels .recharts-cartesian-axis-tick-value",
      ),
    ];
    expect(ticks.map((t) => t.textContent)).toEqual(PERIODS);
  });

  it("shows a legend for two series and none for one", () => {
    renderTwo();
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(
      within(legend)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Net debt", "Gross debt"]);
  });

  it("shows no legend for one series", () => {
    render(
      <TrendChart
        title="Leverage"
        periods={PERIODS}
        series={[series("Net debt", A)]}
        table={[table("Net debt", A_CELLS)]}
      />,
    );
    expect(screen.queryByRole("list", { name: "Legend" })).toBeNull();
  });

  it("folds series beyond six into one Other legend entry, each drawn in the Other style", () => {
    const names = ["a", "b", "c", "d", "e", "f", "g", "h"];
    const { container } = render(
      <TrendChart
        title="Eight"
        periods={PERIODS}
        series={names.map((n) => series(n, A))}
        table={names.map((n) => table(n, A_CELLS))}
      />,
    );
    const items = within(screen.getByRole("list", { name: "Legend" }))
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(items).toEqual(["a", "b", "c", "d", "e", "f", "Other"]);
    const strokes = [...container.querySelectorAll("path.recharts-line-curve")].map((p) =>
      p.getAttribute("stroke"),
    );
    expect(strokes.slice(6)).toEqual(["var(--color-chart-other)", "var(--color-chart-other)"]);
    expect(container.querySelectorAll('[data-marker="none"]')).toHaveLength(0);
  });
});

describe("TrendChart table side", () => {
  it("is the chart by default and the table after the toggle, with n.a. for a null", () => {
    renderTwo();
    expect(screen.queryByRole("table")).toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const grid = screen.getByRole("table");
    const rows = within(grid).getAllByRole("row");
    const head = within(rows[0] as HTMLElement).getAllByRole("columnheader");
    // The shared table heads its row-label column with the chart's title, then the periods.
    expect(head.map((h) => h.textContent)).toEqual(["Leverage", ...PERIODS]);
    const gross = within(rows[2] as HTMLElement);
    expect(gross.getAllByRole("cell").map((c) => c.textContent)).toEqual([
      "5.0",
      "6.0",
      "n.a.not available",
      "8.0",
      "9.0",
      "10.0",
    ]);
    expect(gross.getByRole("rowheader")).toHaveTextContent("Gross debt");
    expect(screen.queryByText("0")).toBeNull();
  });

  it("is the shared table: a sticky row-label column in a relative scroll wrapper", () => {
    renderTwo();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const grid = screen.getByRole("table");
    expect(within(grid).getAllByRole("rowheader")[0]).toHaveClass("sticky", "left-0");
    expect(grid.parentElement).toHaveClass("relative", "overflow-x-auto");
    expect(within(grid).getByText("Leverage", { selector: "caption" })).toBeInTheDocument();
  });

  it("returns to the chart", () => {
    const { container } = renderTwo();
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    fireEvent.click(screen.getByRole("radio", { name: "Chart" }));
    expect(screen.queryByRole("table")).toBeNull();
    expect(container.querySelector("svg.recharts-surface")).not.toBeNull();
  });

  it("keeps a selected view when the selected segment is pressed again", () => {
    renderTwo();
    fireEvent.click(screen.getByRole("radio", { name: "Chart" }));
    expect(screen.getByRole("radio", { name: "Chart" })).toBeChecked();
  });
});

const YTICKS = [
  { value: 0, label: "0" },
  { value: 10, label: "10 m" },
  { value: 20, label: "20 m" },
];

function yTexts(container: HTMLElement): (string | null)[] {
  return [
    ...container.querySelectorAll(
      ".recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value",
    ),
  ].map((t) => t.textContent);
}

describe("TrendChart review fixes", () => {
  it("shows exactly the supplied y tick labels", () => {
    const { container } = render(
      <TrendChart
        title="Leverage"
        periods={PERIODS}
        series={[series("Net debt", A)]}
        table={[table("Net debt", A_CELLS)]}
        yTicks={YTICKS}
      />,
    );
    expect(yTexts(container)).toEqual(["0", "10 m", "20 m"]);
  });

  it("shows no y tick text without yTicks, and keeps the gridlines", () => {
    const { container } = renderTwo();
    expect(yTexts(container)).toEqual([]);
    expect(
      container.querySelectorAll(".recharts-cartesian-grid-horizontal line").length,
    ).toBeGreaterThan(0);
  });

  it("draws no vertical gridlines", () => {
    const { container } = renderTwo();
    expect(container.querySelectorAll(".recharts-cartesian-grid-vertical line")).toHaveLength(0);
  });

  it("carries legend text in text-secondary", () => {
    renderTwo();
    const items = within(screen.getByRole("list", { name: "Legend" })).getAllByRole("listitem");
    for (const li of items) expect(li.className).toContain("text-text-secondary");
  });

  it("names the chart by its title", () => {
    renderTwo();
    expect(screen.getByRole("figure", { name: "Leverage" })).toBeInTheDocument();
  });

  it("throws when series and table names differ or are ordered differently", () => {
    const bad = (rows: ReturnType<typeof table>[]) =>
      render(
        <TrendChart
          title="x"
          periods={PERIODS}
          series={[series("Net debt", A), series("Gross debt", B)]}
          table={rows}
        />,
      );
    expect(() => bad([table("Net debt", A_CELLS)])).toThrow(/same names/);
    expect(() => bad([table("Gross debt", B_CELLS), table("Net debt", A_CELLS)])).toThrow(
      /same names/,
    );
  });

  it("throws when a row's length differs from the periods", () => {
    expect(() =>
      render(
        <TrendChart
          title="x"
          periods={PERIODS}
          series={[series("Net debt", [1, 2])]}
          table={[table("Net debt", A_CELLS)]}
        />,
      ),
    ).toThrow(/periods/);
    expect(() =>
      render(
        <TrendChart
          title="x"
          periods={PERIODS}
          series={[series("Net debt", A)]}
          table={[table("Net debt", ["1"])]}
        />,
      ),
    ).toThrow(/periods/);
  });
});
