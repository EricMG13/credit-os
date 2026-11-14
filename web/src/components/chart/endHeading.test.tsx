import type { ReactElement } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BulletChart } from "./BulletChart";
import { ColumnsChart } from "./ColumnsChart";
import { ComparisonChart } from "./ComparisonChart";
import { DumbbellChart } from "./DumbbellChart";
import { LimitsChart } from "./LimitsChart";
import { PathChart } from "./PathChart";
import { RangeStripChart } from "./RangeStripChart";
import { ScatterPlot } from "./ScatterPlot";
import { StackChart } from "./StackChart";
import { WaterfallChart } from "./WaterfallChart";

const END = <button type="button">Trace</button>;
const TICKS = [
  { value: 0, label: "0" },
  { value: 10, label: "10" },
];
const SCATTER_AXIS = { title: "Net leverage", short: "net leverage", ticks: TICKS };

// Each kind's smallest valid input; every row carries a trace control, and the table prop names
// the end column's heading. The heading is read from the Table side.
const KINDS: [string, (heading: string) => ReactElement][] = [
  [
    "PathChart",
    (h) => (
      <PathChart
        title="T"
        periods={["FY24", "LTM"]}
        series={[{ name: "Base case", values: [2.8, 2.9], labels: ["2.8x", "2.9x"] }]}
        yTicks={TICKS}
        table={{
          head: ["T", "FY24", "LTM"],
          rows: [{ label: "Base case", cells: ["2.8x", "2.9x"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "ColumnsChart",
    (h) => (
      <ColumnsChart
        title="T"
        groups={["2029"]}
        series={[{ name: "Term loans", values: [4], labels: ["4.0"] }]}
        yTicks={TICKS}
        table={{
          head: ["T", "Term loans"],
          rows: [{ label: "2029", cells: ["4.0"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "WaterfallChart",
    (h) => (
      <WaterfallChart
        title="T"
        steps={[{ label: "EBITDA", kind: "total", from: 0, to: 5, text: "5,080" }]}
        yTicks={TICKS}
        legend={{ total: "Total", up: "Increase", down: "Decrease" }}
        table={{
          head: ["T", "Base case"],
          rows: [{ label: "EBITDA", cells: ["5,080"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "StackChart",
    (h) => (
      <StackChart
        title="T"
        parts={[{ name: "Term loans", value: 5, text: "5,000" }]}
        table={{
          head: ["T", "Amount"],
          rows: [{ label: "Term loans", cells: ["5,000"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "ComparisonChart",
    (h) => (
      <ComparisonChart
        title="T"
        cases={["Base case", "Downside"]}
        panels={[{ measure: "Leverage", max: 10, values: [2.6, 3.1], texts: ["2.6x", "3.1x"] }]}
        table={{
          head: ["T", "Base case", "Downside"],
          rows: [{ label: "Leverage", cells: ["2.6x", "3.1x"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "RangeStripChart",
    (h) => (
      <RangeStripChart
        title="T"
        rangeLabel="Range"
        rows={[
          {
            label: "Leverage",
            rangeText: "2.0x to 3.0x",
            range: { low: 2, high: 3 },
            markers: [{ name: "Base case", value: 2.6, text: "2.6x" }],
            axis: { min: 0, max: 10 },
          },
        ]}
        table={{
          head: ["T", "Base case"],
          rows: [{ label: "Leverage", cells: ["2.6x"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "BulletChart",
    (h) => (
      <BulletChart
        title="T"
        rows={[
          {
            label: "Net leverage",
            sub: "Trigger 7.0x",
            value: 5.9,
            target: 7,
            axisMax: 8,
            text: "5.9x",
          },
        ]}
        table={{
          head: ["T", "Latest"],
          rows: [{ label: "Net leverage", cells: ["5.9x"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "DumbbellChart",
    (h) => (
      <DumbbellChart
        title="T"
        names={["FY24", "LTM"]}
        axis={{ min: 0, max: 100 }}
        rows={[{ label: "Airframe", from: 51.9, to: 53.4, text: "51.9% to 53.4%" }]}
        table={{
          head: ["T", "Change"],
          rows: [{ label: "Airframe", cells: ["51.9% to 53.4%"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "LimitsChart",
    (h) => (
      <LimitsChart
        title="T"
        columns={[
          {
            label: "Single issuer",
            exposure: 2.1,
            limit: 3,
            scaleMax: 4,
            exposureText: "2.1%",
            limitText: "limit 3.0%",
          },
        ]}
        table={{
          head: ["Limit", "Exposure", "Limit"],
          rows: [{ label: "Single issuer", cells: ["2.1%", "3.0%"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
  [
    "ScatterPlot",
    (h) => (
      <ScatterPlot
        title="T"
        x={SCATTER_AXIS}
        y={SCATTER_AXIS}
        othersName="Peers"
        points={[{ name: "Issuer", x: 4, y: 5, xText: "4.0x", yText: "5.0x", emphasis: true }]}
        table={{
          head: ["Name", "X", "Y"],
          rows: [{ label: "Issuer", cells: ["4.0x", "5.0x"], end: END }],
          endHeading: h,
        }}
      />
    ),
  ],
];

describe("every table kind passes the table's endHeading to the shared table", () => {
  it.each(KINDS)("%s", (_name, make) => {
    render(make("Open trace"));
    fireEvent.click(screen.getByRole("radio", { name: "Table" }));
    expect(screen.getByRole("columnheader", { name: "Open trace" })).toBeInTheDocument();
  });
});
