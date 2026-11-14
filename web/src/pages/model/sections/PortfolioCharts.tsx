import { LimitsChart } from "@/components/chart/LimitsChart";
import { RangeStripChart } from "@/components/chart/RangeStripChart";
import { ScatterPlot } from "@/components/chart/ScatterPlot";
import type { HoldingsScatter, HoldingsStrips, Limits } from "../slice/types";
import { ChartCard, chartTrace } from "./shared";

/** Exposure against each limit: a column on its own scale with a dashed tick at the limit. */
export function LimitsCard({ data }: { data: Limits }) {
  return (
    <ChartCard>
      <LimitsChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        columns={data.columns.map((c) => ({
          label: c.label,
          exposure: c.exposure,
          limit: c.limit,
          scaleMax: c.scaleMax,
          exposureText: c.exposureText,
          limitText: c.limitText,
        }))}
        table={{
          head: data.head,
          rows: data.columns.map((c) => ({ label: c.label, cells: c.cells })),
        }}
      />
    </ChartCard>
  );
}

/** Leverage against margin: the issuer stands out among the holdings. */
export function ScatterCard({ data }: { data: HoldingsScatter }) {
  return (
    <ChartCard>
      <ScatterPlot
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        x={data.x}
        y={data.y}
        othersName={data.othersName}
        points={data.points.map((p) => ({
          name: p.name,
          x: p.x,
          y: p.y,
          xText: p.xText,
          yText: p.yText,
          emphasis: p.emphasis,
        }))}
        table={{
          head: data.head,
          rows: data.points.map((p) => ({ label: p.name, cells: p.cells })),
        }}
      />
    </ChartCard>
  );
}

/** The issuer against the range across holdings, one strip per measure on its own axis. */
export function StripsCard({ data }: { data: HoldingsStrips }) {
  return (
    <ChartCard>
      <RangeStripChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        rangeLabel={data.rangeLabel}
        rows={data.rows.map((r) => ({
          label: r.label,
          rangeText: r.rangeText,
          range: r.range,
          markers: r.markers,
          axis: r.axis,
        }))}
        table={{
          head: data.head,
          rows: data.rows.map((r) => ({ label: r.label, cells: r.cells })),
        }}
      />
    </ChartCard>
  );
}
