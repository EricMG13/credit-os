import { render, within } from "@testing-library/react";
import { RangeStripChart, type RangeRow } from "./RangeStripChart";
import {
  legendTexts,
  noFocusStopInChart,
  num,
  rowOf,
  tableCells,
  throwsOn,
} from "./RowCharts.helpers";

// All data is copied from the mock's script blocks: Forecast "What drives each case" (drivers),
// Model 4 Portfolio fit (R), Model 2 Analysis (B headroom, D segment margins).
const CASES = ["Base case assumption", "Downside case assumption"];
// label, range text, low, high, base, downside, axis min, axis max, base text, downside text
const DRIVER_DATA: [
  string,
  string,
  number | null,
  number | null,
  number | null,
  number | null,
  number,
  number,
  string | null,
  string | null,
][] = [
  [
    "Organic revenue growth",
    "Past five years: -12% to 18%",
    -12,
    18,
    8,
    -4,
    -15,
    20,
    "8.0%",
    "-4.0%",
  ],
  ["EBITDA margin", "Past five years: 44% to 53%", 44, 53, 53.4, 46.9, 40, 56, "53.4%", "46.9%"],
  [
    "Capital expenditure, share of revenue",
    "Past five years: 1.6% to 2.4%",
    1.6,
    2.4,
    2.1,
    1.7,
    1,
    3,
    "2.1%",
    "1.7%",
  ],
  [
    "Cash interest rate on debt",
    "Past five years: 5.2% to 7.1%",
    5.2,
    7.1,
    5.3,
    6.0,
    4,
    8,
    "5.3%",
    "6.0%",
  ],
  ["Working capital days", "Past five years: 92 to 118", 92, 118, null, null, 80, 130, null, null],
  ["Aftermarket share of revenue", "Range n.a.", null, null, 55, 52, 0, 100, "55%", "52%"],
];
const DRIVERS: RangeRow[] = DRIVER_DATA.map(
  ([label, rangeText, low, high, b, d, min, max, bt, dt]) => ({
    label,
    rangeText,
    range: low === null || high === null ? null : { low, high },
    markers: [
      { name: CASES[0] ?? "", value: b, text: bt },
      { name: CASES[1] ?? "", value: d, text: dt },
    ],
    axis: { min, max },
  }),
);
const DRIVER_TABLE = {
  head: ["Driver, FY26", "Range low", "Range high", "Base case", "Downside case"],
  rows: [
    { label: "Organic revenue growth", cells: ["-12%", "18%", "8.0%", "-4.0%"] },
    { label: "EBITDA margin", cells: ["44%", "53%", "53.4%", "46.9%"] },
    { label: "Capital expenditure, share of revenue", cells: ["1.6%", "2.4%", "2.1%", "1.7%"] },
    { label: "Cash interest rate on debt", cells: ["5.2%", "7.1%", "5.3%", "6.0%"] },
    { label: "Working capital days", cells: ["92", "118", null, null] },
    { label: "Aftermarket share of revenue", cells: [null, null, "55%", "52%"] },
  ],
};
const mk = (b: number | null, d: number | null, bt: string | null, dt: string | null) => [
  { name: CASES[0] ?? "", value: b, text: bt },
  { name: CASES[1] ?? "", value: d, text: dt },
];
describe("RangeStripChart", () => {
  const ui = (rows = DRIVERS, table = DRIVER_TABLE) => (
    <RangeStripChart
      title="What drives each case"
      subtitle="Each FY26 assumption against the range seen over the past five years"
      rangeLabel="Range over five years"
      rows={rows}
      table={table}
    />
  );

  it("draws the strip and a tick per case at positions over each row's own axis", () => {
    render(ui());
    const row = rowOf("EBITDA margin");
    const strip = row.querySelector("[data-range]");
    expect(num(strip, "data-left")).toBeCloseTo(25, 5);
    expect(num(strip, "data-width")).toBeCloseTo(56.25, 5);
    const ticks = row.querySelectorAll("[data-marker]");
    expect([...ticks].map((t) => t.getAttribute("data-name"))).toEqual(CASES);
    expect(num(ticks[0] ?? null, "data-left")).toBeCloseTo(83.75, 5);
    expect(num(ticks[1] ?? null, "data-left")).toBeCloseTo(43.125, 5);
    const growth = rowOf("Organic revenue growth").querySelector("[data-marker]");
    expect(num(growth, "data-left")).toBeCloseTo(65.7142857, 5);
  });

  it("shows every text exactly, with the range text as the sub-label", () => {
    render(ui());
    const texts = (l: string) =>
      [...rowOf(l).querySelectorAll("[data-value]")].map((v) => v.textContent);
    expect(texts("Organic revenue growth")).toEqual(["8.0%", "-4.0%"]);
    expect(within(rowOf("EBITDA margin")).getByText("Past five years: 44% to 53%")).toBeVisible();
    expect(texts("Aftermarket share of revenue")).toEqual(["55%", "52%"]);
  });

  it("draws no strip and no tick where the range is missing", () => {
    render(ui());
    const row = rowOf("Aftermarket share of revenue");
    expect(row.querySelector("[data-range]")).toBeNull();
    expect(row.querySelector("[data-marker]")).toBeNull();
    expect(within(row).getByText("Range n.a.")).toBeVisible();
  });

  it("draws the strip and n.a. for both cases where the markers are missing", () => {
    render(ui());
    const row = rowOf("Working capital days");
    expect(row.querySelector("[data-range]")).not.toBeNull();
    expect(row.querySelector("[data-marker]")).toBeNull();
    expect([...row.querySelectorAll("[data-missing]")].map((m) => m.textContent)).toEqual([
      "n.a.not available",
      "n.a.not available",
    ]);
  });

  it("legends the range and each case, colours the cases from the palette, adds no focus stop", () => {
    const { container } = render(ui());
    expect(legendTexts()).toEqual(["Range over five years", ...CASES]);
    const ticks = rowOf("EBITDA margin").querySelectorAll<HTMLElement>("[data-marker]");
    expect(ticks[0]?.style.backgroundColor).toBe("var(--color-chart-1)");
    expect(ticks[1]?.style.backgroundColor).toBe("var(--color-chart-2)");
    noFocusStopInChart(container);
  });

  it("shows the table side with n.a. where the mock has it", () => {
    render(ui());
    expect(tableCells("Working capital days")).toEqual(["92", "118", "n.a.", "n.a."]);
  });

  it("throws on empty rows, and on a row with no marker", () => {
    const table = { head: ["M"], rows: [] };
    throwsOn(
      <RangeStripChart title="T" rangeLabel="R" rows={[]} table={table} />,
      /rows must not be empty/,
    );
    const bare = { ...(DRIVERS[0] as RangeRow), markers: [] };
    throwsOn(
      <RangeStripChart title="T" rangeLabel="R" rows={[bare]} table={table} />,
      /at least one marker/,
    );
  });

  it("throws on a position outside the axis, a text mismatch, a bad range or other table rows", () => {
    const first = DRIVERS[0] as RangeRow;
    const name = /"Organic revenue growth"/;
    throwsOn(ui([{ ...first, axis: { min: 0, max: 10 } }]), name);
    throwsOn(ui([{ ...first, markers: mk(8, -4, null, "-4.0%") }]), /"Organic.*text/);
    throwsOn(ui([{ ...first, markers: mk(null, -4, "8.0%", "-4.0%") }]), /"Organic.*missing/);
    throwsOn(ui([{ ...first, range: { low: 18, high: -12 } }]), /"Organic.*range/);
    throwsOn(ui([first]), /one row per chart row/);
  });
});

describe("RangeStripChart with one marker (Portfolio fit)", () => {
  // label, range text, low, high, issuer (null = missing), axis max, text; the axis starts at 0.
  const R: [string, string, number, number, number | null, number, string | null][] = [
    ["Net leverage", "Holdings: 2.4x to 6.8x", 2.4, 6.8, 5.9, 8, "5.9x"],
    ["Interest cover", "Holdings: 1.6x to 6.2x", 1.6, 6.2, 2.9, 8, "2.9x"],
    ["EBITDA margin", "Holdings: 9% to 53%", 9, 53.1, 53.1, 60, "53.1%"],
    ["Spread over benchmark", "Holdings: 180 to 520 basis points", 180, 520, null, 600, null],
  ];
  const rows: RangeRow[] = R.map(([label, rangeText, low, high, v, max, text]) => ({
    label,
    rangeText,
    range: { low, high },
    markers: [{ name: "TransDigm", value: v, text }],
    axis: { min: 0, max },
  }));
  const table = {
    head: ["Measure", "Lowest held", "Highest held", "TransDigm"],
    rows: [
      { label: "Net leverage", cells: ["2.4x", "6.8x", "5.9x"] },
      { label: "Interest cover", cells: ["1.6x", "6.2x", "2.9x"] },
      { label: "EBITDA margin", cells: ["9%", "53%", "53.1%"] },
      { label: "Spread over benchmark", cells: ["180 bp", "520 bp", null] },
    ],
  };
  it("draws one tick per row, and n.a. with no tick for the missing issuer", () => {
    render(
      <RangeStripChart title="T" rangeLabel="Range across holdings" rows={rows} table={table} />,
    );
    const left = (l: string) => num(rowOf(l).querySelector("[data-marker]"), "data-left");
    expect(left("Net leverage")).toBeCloseTo(73.75, 5);
    expect(left("Interest cover")).toBeCloseTo(36.25, 5);
    expect(left("EBITDA margin")).toBeCloseTo(88.5, 5);
    expect(rowOf("Spread over benchmark").querySelector("[data-marker]")).toBeNull();
    expect(rowOf("Spread over benchmark")).toHaveTextContent("n.a.");
    expect(legendTexts()).toEqual(["Range across holdings", "TransDigm"]);
  });

  it("draws the value as text alone: no key glyph beside one marker's value or its n.a.", () => {
    render(
      <RangeStripChart title="T" rangeLabel="Range across holdings" rows={rows} table={table} />,
    );
    expect(document.querySelectorAll("[data-value] i")).toHaveLength(0);
  });
});

describe("RangeStripChart key glyphs with two markers", () => {
  it("draws a glyph beside each present value and none beside a missing one", () => {
    const first = DRIVERS[0] as RangeRow;
    const row = { ...first, markers: mk(8, null, "8.0%", null) };
    const only = { head: DRIVER_TABLE.head, rows: DRIVER_TABLE.rows.slice(0, 1) };
    render(
      <RangeStripChart title="T" rangeLabel="Range over five years" rows={[row]} table={only} />,
    );
    const values = [...rowOf(first.label).querySelectorAll("[data-value]")];
    expect(values.map((v) => v.querySelectorAll("i").length)).toEqual([1, 0]);
  });
});

describe("RangeStripChart markers", () => {
  const ui = (emphasised?: number) => (
    <RangeStripChart
      title="What drives each case"
      rangeLabel="Range over five years"
      rows={DRIVERS}
      table={DRIVER_TABLE}
      emphasised={emphasised}
    />
  );
  const markers = (label: string) => [...rowOf(label).querySelectorAll("[data-marker]")];

  it("rings every marker in the card surface, as the mock's 2px white ring, and fades none", () => {
    render(ui());
    for (const m of markers("EBITDA margin")) {
      expect(m.className).toContain("ring-2");
      expect(m.className).toContain("ring-surface-card");
      expect(m.className).not.toMatch(/opacity/);
    }
  });

  it("draws every marker the same size when no case is emphasised", () => {
    render(ui());
    expect(markers("EBITDA margin").map((m) => m.className.includes("w-1.5"))).toEqual([
      false,
      false,
    ]);
  });

  it("makes the emphasised marker wider and taller in every row, and only that one", () => {
    render(ui(1));
    for (const row of DRIVERS.filter(
      (r) => r.range !== null && r.markers.every((m) => m.value !== null),
    )) {
      const [first, second] = markers(row.label);
      expect(first?.classList.contains("w-1")).toBe(true);
      expect(first?.classList.contains("h-6")).toBe(true);
      expect(second?.classList.contains("w-1.5")).toBe(true);
      expect(second?.classList.contains("h-7")).toBe(true);
    }
  });

  it("sets the other case's value text in the tertiary colour, and every value alike with no emphasis", () => {
    const tone = () =>
      [...rowOf("EBITDA margin").querySelectorAll("[data-value]")].map((v) =>
        v.classList.contains("text-text-tertiary"),
      );
    const { unmount } = render(ui());
    expect(tone()).toEqual([false, false]);
    unmount();
    render(ui(0));
    expect(tone()).toEqual([false, true]);
  });

  it("throws on an emphasised position the rows have no marker at", () => {
    expect(() => render(ui(2))).toThrow(/emphasised/);
  });
});
