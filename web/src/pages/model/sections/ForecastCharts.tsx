import { PathChart } from "@/components/chart/PathChart";
import { RangeStripChart } from "@/components/chart/RangeStripChart";
import { WaterfallChart } from "@/components/chart/WaterfallChart";
import type { Bridge, CaseCard, EbitdaPaths, HoldingsStrips, InterestCover } from "../slice/types";
import { ChartCard, END_HEADING, chartTrace, rowTrace } from "./shared";

/** Each FY26 assumption against its five-year range, a marker per case; the chosen case stands out. */
export function DriversCard({ data, chosen }: { data: HoldingsStrips; chosen: number }) {
  return (
    <ChartCard>
      <RangeStripChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        rangeLabel={data.rangeLabel}
        emphasised={chosen}
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

/** One line for the chosen case; the table holds both. */
export function CoverCard({
  data,
  periods,
  cases,
  chosen,
}: {
  data: InterestCover;
  periods: string[];
  cases: readonly CaseCard[];
  chosen: number;
}) {
  const line = data.cases[chosen];
  const name = cases[chosen]?.name;
  if (line === undefined || name === undefined) {
    throw new Error(`no interest cover for case ${String(chosen)}`);
  }
  return (
    <ChartCard>
      <PathChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        periods={periods}
        series={[{ name, values: line.values, labels: line.labels }]}
        divider={data.divider}
        yTicks={data.yTicks}
        table={{ head: data.head, rows: data.rows }}
      />
    </ChartCard>
  );
}

/** Both cases, whichever is chosen. */
export function PathsCard({ data, periods }: { data: EbitdaPaths; periods: string[] }) {
  return (
    <ChartCard>
      <PathChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        periods={periods}
        series={data.series}
        divider={data.divider}
        yTicks={data.yTicks}
        table={{ head: data.head, rows: data.rows }}
      />
    </ChartCard>
  );
}

const LEGEND = { total: "Total", down: "Cash out (minus)", up: "Cash in (plus)" };

/** The FY26 cash flow walk for the chosen case; the table holds both. */
export function WalkCard({ data, chosen }: { data: Bridge; chosen: number }) {
  const steps = data.caseSteps[chosen];
  if (steps === undefined) throw new Error(`no steps for case ${String(chosen)}`);
  return (
    <ChartCard>
      <WaterfallChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        steps={steps}
        yTicks={data.yTicks}
        legend={LEGEND}
        table={{
          head: data.head,
          endHeading: END_HEADING,
          rows: data.rows.map((row) => ({
            label: row.label,
            cells: row.cells,
            end: rowTrace(row.trace, row.label, data.title),
          })),
        }}
      />
    </ChartCard>
  );
}
