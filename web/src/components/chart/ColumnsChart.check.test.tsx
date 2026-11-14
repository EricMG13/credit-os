import { render } from "@testing-library/react";
import { ColumnsChart } from "./ColumnsChart";
import { barOf, bars, renderMat, renderRec } from "./ColumnsChart.fixtures";

describe("ColumnsChart check", () => {
  const base = {
    title: "T",
    groups: ["G1", "G2"],
    yTicks: [],
    table: {
      head: ["T", "A"],
      rows: [
        { label: "G1", cells: ["1"] },
        { label: "G2", cells: ["2"] },
      ],
    },
  };
  function throwsOn(ui: React.ReactElement, pattern: RegExp) {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() => render(ui)).toThrow(pattern);
    quiet.mockRestore();
  }
  it("throws when values do not match the groups", () => {
    throwsOn(
      <ColumnsChart {...base} series={[{ name: "A", values: [1], labels: ["1", "2"] }]} />,
      /"A".*per group/,
    );
  });
  it("throws when labels do not match the groups", () => {
    throwsOn(
      <ColumnsChart {...base} series={[{ name: "A", values: [1, 2], labels: ["1"] }]} />,
      /"A".*per group/,
    );
  });
  it("throws when a present value has no label", () => {
    throwsOn(
      <ColumnsChart {...base} series={[{ name: "A", values: [1, 2], labels: ["1", null] }]} />,
      /"A".*"G2".*label/,
    );
  });
  it("throws when a missing value carries a label", () => {
    throwsOn(
      <ColumnsChart {...base} series={[{ name: "A", values: [1, null], labels: ["1", "2"] }]} />,
      /"A".*"G2".*missing/,
    );
  });
  it("throws when two series share a name", () => {
    const s = { name: "A", values: [1, 2], labels: ["1", "2"] };
    throwsOn(<ColumnsChart {...base} series={[s, s]} />, /distinct/);
  });
  it("throws when the table has no row per group", () => {
    throwsOn(
      <ColumnsChart
        {...base}
        table={{ head: ["T", "A"], rows: [{ label: "G1", cells: ["1"] }] }}
        series={[{ name: "A", values: [1, 2], labels: ["1", "2"] }]}
      />,
      /table.*group/,
    );
  });
});

describe("ColumnsChart table orientation check", () => {
  const series = [{ name: "A", values: [1, 2], labels: ["1", "2"] }];
  const row1 = { label: "G1", cells: ["1"] };
  const row2 = { label: "G2", cells: ["2"] };
  const rows = [row1, row2];
  function throwsOn(
    table: { head: string[]; rows: typeof rows },
    groups: string[],
    pattern: RegExp,
  ) {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(<ColumnsChart title="T" groups={groups} series={series} yTicks={[]} table={table} />),
    ).toThrow(pattern);
    quiet.mockRestore();
  }
  it("throws when the table columns are not the series names", () => {
    throwsOn({ head: ["T", "B"], rows }, ["G1", "G2"], /series names/);
  });
  it("throws when the row labels are not the groups in order", () => {
    throwsOn({ head: ["T", "A"], rows: [row2, row1] }, ["G1", "G2"], /labelled with the group/);
  });
  it("throws when a row has the wrong number of cells", () => {
    throwsOn(
      { head: ["T", "A"], rows: [{ label: "G1", cells: ["1", "x"] }, row2] },
      ["G1", "G2"],
      /"G1".*one cell per series/,
    );
  });
  it("throws on repeated group names", () => {
    throwsOn({ head: ["T", "A"], rows }, ["G1", "G1"], /group names must be distinct/);
  });
  it("throws on a negative value", () => {
    const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
    expect(() =>
      render(
        <ColumnsChart
          title="T"
          groups={["G1", "G2"]}
          series={[{ name: "A", values: [1, -2], labels: ["1", "-2"] }]}
          yTicks={[]}
          table={{ head: ["T", "A"], rows }}
        />,
      ),
    ).toThrow(/"G2".*zero or more/);
    quiet.mockRestore();
  });
});

/** The distance from the top of a bar to the baseline of its own label. */
function labelGap(container: HTMLElement, series: string, group: string): number {
  const bar = barOf(container, series, group);
  const cx = Number(bar?.getAttribute("x")) + Number(bar?.getAttribute("width")) / 2;
  const text = [...container.querySelectorAll(`[data-label][data-series="${series}"]`)].find(
    (t) => Math.abs(Number(t.getAttribute("x")) - cx) < 0.5,
  );
  const top =
    Number(/^M[-\d.]+,([-\d.]+)/.exec(bar?.getAttribute("d") ?? "")?.[1]) -
    Number(bar?.getAttribute("height"));
  return top - Number(text?.getAttribute("y"));
}

describe("ColumnsChart three-series labels", () => {
  it("raises the middle label 16px above where an outer label would sit", () => {
    const { container } = renderMat();
    const gap = (series: string, group: string) => labelGap(container, series, group);
    expect(gap("Secured notes", "2029") - gap("Subordinated notes", "2029")).toBe(16);
    expect(gap("Term loans", "2030")).toBe(gap("Subordinated notes", "2029"));
  });

  it("leaves the two-series labels all at one height above their bars", () => {
    const { container } = renderRec();
    const gaps = bars(container).map((b) =>
      labelGap(container, b.getAttribute("data-series") ?? "", b.getAttribute("data-group") ?? ""),
    );
    expect(gaps).toHaveLength(5);
    expect(gaps[0]).toBeGreaterThan(0);
    expect(new Set(gaps).size).toBe(1);
  });
});

describe("ColumnsChart narrow plot", () => {
  const Original = globalThis.ResizeObserver;
  beforeEach(() => {
    class Narrow implements ResizeObserver {
      constructor(private readonly cb: ResizeObserverCallback) {}
      observe(target: Element) {
        const rect = {
          width: 320,
          height: 240,
          x: 0,
          y: 0,
          top: 0,
          left: 0,
          right: 320,
          bottom: 240,
        };
        const size = [{ inlineSize: 320, blockSize: 240 }];
        this.cb(
          [
            {
              target,
              contentRect: { ...rect, toJSON: () => rect },
              borderBoxSize: size,
              contentBoxSize: size,
              devicePixelContentBoxSize: size,
            },
          ],
          this,
        );
      }
      unobserve() {}
      disconnect() {}
    }
    globalThis.ResizeObserver = Narrow;
  });
  afterEach(() => {
    globalThis.ResizeObserver = Original;
  });

  it("keeps the n.a. in the missing bar's slot, one bar and gap left of the next bar", () => {
    const { container } = renderMat();
    const na = container.querySelector("[data-missing]");
    const next = barOf(container, "Secured notes", "2026");
    const nextCentre = Number(next?.getAttribute("x")) + Number(next?.getAttribute("width")) / 2;
    // Recharts places bars to within a pixel of the arithmetic.
    expect(Math.abs(Number(na?.getAttribute("x")) - (nextCentre - 24))).toBeLessThanOrEqual(1);
  });
});
