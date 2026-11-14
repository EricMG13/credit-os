import { render, within } from "@testing-library/react";
import { DumbbellChart, type DumbbellRow } from "./DumbbellChart";
import {
  legendTexts,
  noFocusStopInChart,
  num,
  rowOf,
  tableCells,
  throwsOn,
} from "./RowCharts.helpers";

const DUMBBELLS: DumbbellRow[] = [
  { label: "Power and control", from: 55.8, to: 57.5, text: "55.8% to 57.5%" },
  { label: "Airframe", from: 51.9, to: 53.4, text: "51.9% to 53.4%" },
  { label: "Non-aviation", from: 41.2, to: 38.6, text: "41.2% to 38.6%" },
  { label: "Acquired businesses", from: null, to: 44.0, text: "n.a. to 44.0%" },
];
const DUMB_TABLE = {
  head: ["Segment", "FY24", "Latest twelve months"],
  rows: [
    { label: "Power and control", cells: ["55.8%", "57.5%"] },
    { label: "Airframe", cells: ["51.9%", "53.4%"] },
    { label: "Non-aviation", cells: ["41.2%", "38.6%"] },
    { label: "Acquired businesses", cells: [null, "44.0%"] },
  ],
};

describe("DumbbellChart", () => {
  const ui = (rows = DUMBBELLS, table = DUMB_TABLE) => (
    <DumbbellChart
      title="EBITDA margin by segment"
      names={["FY24", "Latest twelve months"]}
      axis={{ min: 30, max: 60 }}
      rows={rows}
      table={table}
    />
  );

  it("joins a ring for the earlier and a filled mark for the later period, either order", () => {
    const { container } = render(ui());
    const row = rowOf("Non-aviation");
    expect(num(row.querySelector('[data-mark="from"]'), "data-left")).toBeCloseTo(37.3333333, 5);
    expect(num(row.querySelector('[data-mark="to"]'), "data-left")).toBeCloseTo(28.6666667, 5);
    const line = row.querySelector("[data-line]");
    expect(num(line, "data-left")).toBeCloseTo(28.6666667, 5);
    expect(num(line, "data-width")).toBeCloseTo(8.6666667, 5);
    expect(within(row).getByText("41.2% to 38.6%")).toBeVisible();
    // The earlier mark is a hollow square on the card colour, the later a filled circle.
    expect(row.querySelector('[data-mark="from"]')).toHaveClass("rounded-[1px]", "bg-surface-card");
    expect(row.querySelector('[data-mark="to"]')).toHaveClass("rounded-full");
    expect(legendTexts()).toEqual(["FY24", "Latest twelve months"]);
    noFocusStopInChart(container);
  });

  it("draws one mark, no line and n.a. when the earlier value is missing", () => {
    render(ui());
    const row = rowOf("Acquired businesses");
    expect(row.querySelector('[data-mark="from"]')).toBeNull();
    expect(row.querySelectorAll("[data-mark]")).toHaveLength(1);
    expect(row.querySelector("[data-line]")).toBeNull();
    expect(row.querySelectorAll("[data-missing]")).toHaveLength(1);
    expect(within(row).getByText("n.a. to 44.0%")).toBeVisible();
  });

  it("shows the table side, n.a. for the missing value", () => {
    render(ui());
    expect(tableCells("Acquired businesses")).toEqual(["n.a.", "44.0%"]);
  });

  it("throws on a position outside the axis, both values missing or an empty text", () => {
    const first = DUMBBELLS[0] as DumbbellRow;
    throwsOn(ui([{ ...first, to: 70 }]), /"Power and control".*axis/);
    throwsOn(ui([{ ...first, from: null, to: null }]), /"Power and control".*both/);
    throwsOn(ui([{ ...first, text: "" }]), /"Power and control".*text/);
  });

  it("throws on empty rows", () => {
    const table = { head: ["M"], rows: [] };
    throwsOn(
      <DumbbellChart
        title="T"
        names={["a", "b"]}
        axis={{ min: 0, max: 1 }}
        rows={[]}
        table={table}
      />,
      /rows must not be empty/,
    );
  });
});
