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
    expect(head.map((h) => h.textContent)).toEqual(PERIODS);
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
