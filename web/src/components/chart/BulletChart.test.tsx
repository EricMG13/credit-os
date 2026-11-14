import { render, within } from "@testing-library/react";
import { BulletChart, type BulletRow } from "./BulletChart";
import { noFocusStopInChart, num, rowOf, tableCells, throwsOn } from "./RowCharts.helpers";

const BULLETS: BulletRow[] = [
  {
    label: "Net leverage",
    sub: "Downgrade trigger above 7.0x",
    value: 5.9,
    target: 7.0,
    axisMax: 8,
    text: "5.9x of 7.0x",
  },
  {
    label: "Interest cover",
    sub: "Downgrade trigger below 2.0x",
    value: 2.9,
    target: 2.0,
    axisMax: 4,
    text: "2.9x against 2.0x",
  },
  {
    label: "Free cash flow to debt",
    sub: "Upgrade trigger above 10%",
    value: 6.6,
    target: 10,
    axisMax: 12,
    text: "6.6% of 10%",
  },
  {
    label: "Secured net leverage",
    sub: "Covenant limit 7.25x",
    value: null,
    target: 7.25,
    axisMax: 8,
    text: null,
  },
];
const BULLET_TABLE = {
  head: ["Measure", "Latest twelve months", "Level that matters"],
  rows: [
    { label: "Net leverage", cells: ["5.9x", "Downgrade above 7.0x"] },
    { label: "Interest cover", cells: ["2.9x", "Downgrade below 2.0x"] },
    { label: "Free cash flow to debt", cells: ["6.6%", "Upgrade above 10%"] },
    { label: "Secured net leverage", cells: [null, "Covenant limit 7.25x"] },
  ],
};
describe("BulletChart", () => {
  const ui = (rows = BULLETS, table = BULLET_TABLE) => (
    <BulletChart title="Headroom to covenants and rating triggers" rows={rows} table={table} />
  );

  it("draws a bar from zero to the value and a dashed target line", () => {
    const { container } = render(ui());
    const row = rowOf("Net leverage");
    expect(num(row.querySelector("[data-bar]"), "data-width")).toBeCloseTo(73.75, 5);
    expect(num(row.querySelector("[data-target]"), "data-left")).toBeCloseTo(87.5, 5);
    expect(row.querySelector("[data-target]")).toHaveClass("border-dashed");
    expect(within(row).getByText("5.9x of 7.0x")).toBeVisible();
    expect(within(row).getByText("Downgrade trigger above 7.0x")).toBeVisible();
    noFocusStopInChart(container);
  });

  it("draws no bar and n.a. in the bar's place and the value column, and the target line stays", () => {
    render(ui());
    const row = rowOf("Secured net leverage");
    expect(row.querySelector("[data-bar]")).toBeNull();
    const missing = row.querySelectorAll("[data-missing]");
    expect(missing).toHaveLength(2);
    expect(row.querySelector("[data-target]")?.parentElement).toContainElement(
      missing[0] as HTMLElement,
    );
    expect(num(row.querySelector("[data-target]"), "data-left")).toBeCloseTo(90.625, 5);
  });

  it("shows the table side, n.a. for the missing value", () => {
    render(ui());
    expect(tableCells("Secured net leverage")).toEqual(["n.a.", "Covenant limit 7.25x"]);
  });

  it("throws on a value or target outside the axis, or a text that disagrees with the value", () => {
    const first = BULLETS[0] as BulletRow;
    throwsOn(ui([{ ...first, value: 9 }]), /"Net leverage".*axis/);
    throwsOn(ui([{ ...first, target: 9 }]), /"Net leverage".*axis/);
    throwsOn(ui([{ ...first, value: -1 }]), /"Net leverage".*axis/);
    throwsOn(ui([{ ...first, text: null }]), /"Net leverage".*text/);
    throwsOn(ui([{ ...first, value: null }]), /"Net leverage".*missing/);
  });

  it("throws on empty rows", () => {
    const table = { head: ["M"], rows: [] };
    throwsOn(<BulletChart title="T" rows={[]} table={table} />, /rows must not be empty/);
  });
});
