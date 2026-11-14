import { ColumnsChart } from "@/components/chart/ColumnsChart";
import type { ColumnsData } from "../slice/types";
import { ChartCard, END_HEADING, chartTrace, rowTrace } from "./shared";

/** Bars by group and series in a card; the table is the labels as drawn, one row per group. */
export function ColumnsCard({ data }: { data: ColumnsData }) {
  return (
    <ChartCard>
      <ColumnsChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        groups={data.groups.map((g) => g.label)}
        series={data.series}
        yTicks={data.yTicks}
        table={{
          head: [data.head, ...data.series.map((s) => s.name)],
          endHeading: END_HEADING,
          rows: data.groups.map((group, g) => ({
            label: group.label,
            cells: data.series.map((s) => s.labels[g] ?? null),
            end: rowTrace(group.trace, group.label, data.title),
          })),
        }}
      />
    </ChartCard>
  );
}
