import { LimitsChart } from "@/components/chart/LimitsChart";
import { RangeStripChart } from "@/components/chart/RangeStripChart";
import { ScatterPlot } from "@/components/chart/ScatterPlot";
import { GapPanel } from "@/components/gap/GapPanel";
import {
  isGap,
  type HoldingsScatter,
  type HoldingsStrips,
  type Limits,
  type SectionGap,
} from "../slice/types";
import { ChartCard, SectionHeading, chartTrace } from "./shared";

/** A section the run could not fill: its title and the reason as given, and no chart. */
function GapCard({ gap }: SectionGap) {
  return (
    <ChartCard>
      <div className="flex flex-col gap-4">
        <SectionHeading as="h3">{gap.title}</SectionHeading>
        <GapPanel reason={gap.reason} />
      </div>
    </ChartCard>
  );
}

/** Exposure against each limit: a column on its own scale with a dashed tick at the limit. */
export function LimitsCard({ data }: { data: Limits | SectionGap }) {
  if (isGap(data)) return <GapCard gap={data.gap} />;
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
export function ScatterCard({ data }: { data: HoldingsScatter | SectionGap }) {
  if (isGap(data)) return <GapCard gap={data.gap} />;
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

/**
 * One strip per measure on its own axis, against the range across holdings or a five-year range;
 * `emphasised` is the chosen case, whose marker stands out.
 */
export function StripsCard({ data, emphasised }: { data: HoldingsStrips; emphasised?: number }) {
  return (
    <ChartCard>
      <RangeStripChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        rangeLabel={data.rangeLabel}
        emphasised={emphasised}
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
