import { fireEvent, render, screen, within } from "@testing-library/react";
import type { TableRowData } from "./ChartTable";
import { LimitsChart, type LimitColumn } from "./LimitsChart";

// Labels and strings are copied from the mock's script block (Model 4 Portfolio fit, "Exposure
// against limits"). Each column's scaleMax is a position-only number: the mock draws the limit at
// 80% of the column (limit times 1.25) and a bar with no limit at 70%.
const COLUMNS: LimitColumn[] = [
  {
    label: "Single issuer",
    exposure: 2.1,
    limit: 3.0,
    scaleMax: 3.75,
    exposureText: "2.1%",
    limitText: "limit 3.0%",
  },
  {
    label: "Aerospace and defence",
    exposure: 9.4,
    limit: 12.0,
    scaleMax: 15,
    exposureText: "9.4%",
    limitText: "limit 12.0%",
  },
  {
    label: "Rated single B",
    exposure: 31.0,
    limit: 35.0,
    scaleMax: 43.75,
    exposureText: "31.0%",
    limitText: "limit 35.0%",
  },
  {
    label: "United States",
    exposure: 58.0,
    limit: null,
    scaleMax: 82.8,
    exposureText: "58.0%",
    limitText: null,
  },
  {
    label: "Subordinated debt",
    exposure: null,
    limit: 10.0,
    scaleMax: 12.5,
    exposureText: null,
    limitText: "limit 10.0%",
  },
];
const TABLE = {
  head: ["Limit", "Exposure", "Limit"],
  rows: [
    { label: "Single issuer", cells: ["2.1%", "3.0%"] },
    { label: "Aerospace and defence", cells: ["9.4%", "12.0%"] },
    { label: "Rated single B", cells: ["31.0%", "35.0%"] },
    { label: "United States", cells: ["58.0%", null] },
    { label: "Subordinated debt", cells: [null, "10.0%"] },
  ],
};
const US_ROW: TableRowData = { label: "United States", cells: ["58.0%", null] };
type Props = Parameters<typeof LimitsChart>[0];
const base = {
  title: "Exposure against limits",
  subtitle: "Share of the portfolio after the proposed position; each limit on its own scale",
  columns: COLUMNS,
  table: TABLE,
} satisfies Props;

function column(container: HTMLElement, label: string) {
  const el = [...container.querySelectorAll("[data-column]")].find(
    (c) => c.getAttribute("data-column") === label,
  );
  if (el === undefined) throw new Error(`no column ${label}`);
  return el as HTMLElement;
}

describe("LimitsChart chart side", () => {
  it("draws the bar and the dashed tick with the exact texts, each on its own scale", () => {
    const { container } = render(<LimitsChart {...base} />);
    const col = column(container, "Single issuer");
    expect(col.querySelector("[data-bar]")?.textContent).toBe("2.1%");
    expect(col.querySelector("[data-tick]")?.textContent).toBe("limit 3.0%");
    const at = (el: Element | null, name: string) => Number(el?.getAttribute(name));
    expect(at(col.querySelector("[data-bar]"), "data-height")).toBeCloseTo(56);
    expect(at(col.querySelector("[data-tick]"), "data-at")).toBeCloseTo(80);
    const other = column(container, "Aerospace and defence");
    expect(at(other.querySelector("[data-tick]"), "data-at")).toBeCloseTo(80);
    expect(at(other.querySelector("[data-bar]"), "data-height")).toBeCloseTo(62.67, 1);
  });

  it("draws the bar with 'limit n.a.' and no tick when the limit is missing", () => {
    const { container } = render(<LimitsChart {...base} />);
    const col = column(container, "United States");
    expect(col.querySelector("[data-exposure]")?.textContent).toBe("58.0%");
    expect(col.querySelector("[data-tick]")).toBeNull();
    expect(col.querySelector("[data-limit-missing]")?.textContent).toContain("n.a.");
    expect(col.textContent).toContain("limit n.a.");
  });

  it("reserves headroom so a bar at 95% keeps its two labels inside the plot", () => {
    const tall: LimitColumn = {
      label: "United States",
      exposure: 95,
      limit: null,
      scaleMax: 100,
      exposureText: "58.0%",
      limitText: null,
    };
    const { container } = render(
      <LimitsChart {...base} columns={[tall]} table={{ ...TABLE, rows: [US_ROW] }} />,
    );
    const col = column(container, "United States");
    const plot = container.querySelector("[data-plot]");
    const track = col.querySelector("[data-track]");
    const labels = col.querySelector("[data-exposure]")?.parentElement;
    expect(plot?.contains(labels ?? null)).toBe(true);
    // The bar is positioned inside the track, and the track starts below the 36px the two
    // stacked 16px label lines and their 4px gap need: the column's top padding.
    expect(track?.contains(col.querySelector("[data-bar]"))).toBe(true);
    expect(col).toHaveClass("pt-9");
    expect(col.querySelector("[data-bar]")).toHaveAttribute("data-height", "95");
  });

  it("keeps 'limit n.a.' clear of the exposure label when the bar is near the top", () => {
    const tall: LimitColumn = {
      label: "United States",
      exposure: 95,
      limit: null,
      scaleMax: 100,
      exposureText: "58.0%",
      limitText: null,
    };
    const { container } = render(
      <LimitsChart {...base} columns={[tall]} table={{ ...TABLE, rows: [US_ROW] }} />,
    );
    const col = column(container, "United States");
    const bar = col.querySelector("[data-bar]");
    const note = col.querySelector("[data-limit-missing]");
    // The note is placed inside the bar's column above the exposure label: both are children of
    // the bar, so they stack and cannot overlap.
    expect(bar?.contains(note ?? null)).toBe(true);
    expect(bar?.textContent).toContain("58.0%");
    expect(bar?.textContent).toContain("limit n.a.");
  });

  it("draws n.a. and no bar when the exposure is missing, and keeps the tick", () => {
    const { container } = render(<LimitsChart {...base} />);
    const col = column(container, "Subordinated debt");
    expect(col.querySelector("[data-bar]")).toBeNull();
    expect(col.querySelector("[data-missing]")?.textContent).toContain("n.a.");
    expect(col.querySelector("[data-tick]")?.textContent).toBe("limit 10.0%");
  });

  it("is plain text with no focus stop, names the columns and shows the subtitle", () => {
    const { container } = render(<LimitsChart {...base} />);
    expect(container.querySelector("[data-column] [tabindex], [data-column][tabindex]")).toBeNull();
    expect(screen.getByText("Aerospace and defence")).toBeInTheDocument();
    expect(screen.getByText(base.subtitle)).toBeInTheDocument();
  });
});

describe("LimitsChart table side", () => {
  it("shows the mock's table with n.a. in the same cells", () => {
    render(<LimitsChart {...base} />);
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    const row = screen.getByRole("row", { name: /United States/ });
    expect(
      within(row)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["58.0%", "n.a.not available"]);
  });
});

describe("LimitsChart check", () => {
  const bad = (columns: LimitColumn[], table = TABLE) =>
    expect(() => render(<LimitsChart {...base} columns={columns} table={table} />));
  const first = COLUMNS[0] as LimitColumn;
  it("throws for a text on a missing value, a missing text, or a value past its scale", () => {
    bad([{ ...first, exposure: null }, ...COLUMNS.slice(1)]).toThrow(/Single issuer/);
    bad([{ ...first, limitText: null }, ...COLUMNS.slice(1)]).toThrow(/Single issuer/);
    bad([{ ...first, exposure: 9 }, ...COLUMNS.slice(1)]).toThrow(/scale/);
    bad([{ ...first, exposure: -1 }, ...COLUMNS.slice(1)]).toThrow(/zero or more/);
    bad([{ ...first, scaleMax: 0 }, ...COLUMNS.slice(1)]).toThrow(/scale/);
  });
  it("throws for repeated labels and a table that does not match the columns", () => {
    bad([first, first]).toThrow(/distinct/);
    bad(COLUMNS, { ...TABLE, rows: TABLE.rows.slice(1) }).toThrow(/table/);
    bad(COLUMNS, {
      ...TABLE,
      rows: [{ label: "Single issuer", cells: ["2.2%", "3.0%"] }, ...TABLE.rows.slice(1)],
    }).toThrow(/table/);
  });
});
