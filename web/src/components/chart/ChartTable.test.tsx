import { render, screen, within } from "@testing-library/react";
import { ChartTable } from "./ChartTable";
import type { TableCell, TableRowData } from "./ChartTable";

const HEAD = ["Interest cover", "FY22", "FY23"];

describe("ChartTable", () => {
  it("draws a string as given, right-aligned, under a screen-reader caption", () => {
    render(
      <ChartTable
        caption="Interest cover"
        head={HEAD}
        rows={[{ label: "Base case", cells: ["2.6x", "2.8x"] }]}
      />,
    );
    expect(screen.getByRole("table", { name: "Interest cover" })).toBeInTheDocument();
    const cell = screen.getByRole("cell", { name: "2.6x" });
    expect(cell).toHaveClass("text-right", "tabular-nums");
    expect(screen.getByRole("rowheader", { name: "Base case" })).toHaveAttribute("scope", "row");
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(HEAD);
  });

  it("draws null as n.a. for the eye and not available for a screen reader", () => {
    render(
      <ChartTable caption="C" head={HEAD} rows={[{ label: "Base case", cells: ["2.6x", null] }]} />,
    );
    const cell = screen.getAllByRole("cell")[1];
    expect(within(cell as HTMLElement).getByText("n.a.")).toBeVisible();
    expect(within(cell as HTMLElement).getByText("not available")).toHaveClass("sr-only");
  });

  it("draws a withheld cell with the kit badge and no reason", () => {
    const cells: TableCell[] = ["2.6x", { withheld: true }];
    render(<ChartTable caption="C" head={HEAD} rows={[{ label: "Base case", cells }]} />);
    expect(screen.getByText("Withheld")).toBeInTheDocument();
  });

  it("draws a gap cell with the kit gap badge", () => {
    render(
      <ChartTable
        caption="C"
        head={HEAD}
        rows={[{ label: "Base case", cells: [{ gap: true }, "2.8x"] }]}
      />,
    );
    expect(screen.getByText("Not established for this run")).toBeInTheDocument();
  });

  it("adds a last cell when a row carries end, and no column when none does", () => {
    const { rerender } = render(
      <ChartTable
        caption="C"
        head={HEAD}
        endHeading="Sources"
        rows={[
          { label: "A", cells: ["1", "2"], end: <button type="button">Trace A</button> },
          { label: "B", cells: ["3", "4"] },
        ]}
      />,
    );
    expect(screen.getByRole("button", { name: "Trace A" })).toBeInTheDocument();
    expect(screen.getAllByRole("row").map((r) => r.children.length)).toEqual([4, 4, 4]);
    rerender(<ChartTable caption="C" head={HEAD} rows={[{ label: "A", cells: ["1", "2"] }]} />);
    expect(screen.getAllByRole("row").map((r) => r.children.length)).toEqual([3, 3]);
  });

  it("heads the end column with a column header whose text the caller supplies", () => {
    render(
      <ChartTable
        caption="C"
        head={HEAD}
        endHeading="Trace"
        rows={[{ label: "A", cells: ["1", "2"], end: <button type="button">Trace A</button> }]}
      />,
    );
    const heading = screen.getByRole("columnheader", { name: "Trace" });
    expect(heading).toHaveAttribute("scope", "col");
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      ...HEAD,
      "Trace",
    ]);
  });

  it("throws when a row has end and no end heading is given", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(
        <ChartTable
          caption="C"
          head={HEAD}
          rows={[{ label: "A", cells: ["1", "2"], end: <button type="button">Trace A</button> }]}
        />,
      ),
    ).toThrow(/endHeading/);
    quiet.mockRestore();
  });

  it("throws on an empty rows array", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(<ChartTable caption="C" head={HEAD} rows={[]} />)).toThrow(
      /at least one row/,
    );
    quiet.mockRestore();
  });

  it("throws, naming the row, on an empty-string cell", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(
        <ChartTable caption="C" head={HEAD} rows={[{ label: "Blank row", cells: ["", "2"] }]} />,
      ),
    ).toThrow(/Blank row/);
    quiet.mockRestore();
  });

  it("throws on a cell of an unknown shape instead of drawing a gap", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const odd = { reason: "x" } as unknown as TableCell;
    expect(() =>
      render(<ChartTable caption="C" head={HEAD} rows={[{ label: "A", cells: ["1", odd] }]} />),
    ).toThrow(/unknown cell/);
    quiet.mockRestore();
  });

  it("positions the scroll wrapper so hidden text cannot widen the page", () => {
    render(<ChartTable caption="C" head={HEAD} rows={[{ label: "A", cells: ["1", null] }]} />);
    const wrapper = screen.getByRole("table").parentElement;
    expect(wrapper).toHaveClass("relative", "overflow-x-auto");
  });

  it("keeps the row label sticky on the card colour and heads columns in tertiary text", () => {
    render(<ChartTable caption="C" head={HEAD} rows={[{ label: "A", cells: ["1", "2"] }]} />);
    const rowLabel = screen.getByRole("rowheader", { name: "A" });
    expect(rowLabel).toHaveClass("sticky", "left-0", "bg-surface-card");
    const heads = screen.getAllByRole("columnheader");
    for (const h of heads) expect(h).toHaveClass("text-text-tertiary");
    expect(heads[0]).toHaveClass("sticky", "left-0", "bg-surface-card");
  });

  it("throws, naming the row, when a row has the wrong number of cells", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(<ChartTable caption="C" head={HEAD} rows={[{ label: "Ragged row", cells: ["1"] }]} />),
    ).toThrow(/Ragged row/);
    quiet.mockRestore();
  });

  it("draws two rows that share a label", () => {
    const rows: TableRowData[] = [
      { label: "Base case", cells: ["1", "2"] },
      { label: "Base case", cells: ["3", "4"] },
    ];
    render(<ChartTable caption="C" head={HEAD} rows={rows} />);
    expect(screen.getAllByRole("rowheader", { name: "Base case" })).toHaveLength(2);
    expect(screen.getByRole("cell", { name: "4" })).toBeInTheDocument();
  });
});
