import { ComparisonChart } from "@/components/chart/ComparisonChart";
import type { CaseCard, Comparison } from "../slice/types";
import { ChartCard, END_HEADING, chartTrace, rowTrace } from "./shared";

/** The two cases side by side, one panel per measure; it shows both cases whichever is chosen. */
export function CaseComparison({ data, cases }: { data: Comparison; cases: readonly CaseCard[] }) {
  const [first, second] = cases;
  if (first === undefined || second === undefined || cases.length !== 2) {
    throw new Error("the side by side chart needs exactly two cases");
  }
  const names: [string, string] = [first.name, second.name];
  return (
    <ChartCard>
      <ComparisonChart
        title={data.title}
        as="h3"
        subtitle={data.subtitle}
        note={data.note}
        actions={chartTrace(data.trace, data.title)}
        cases={names}
        rowLabels={data.rowLabels}
        panels={data.panels}
        table={{
          head: [data.tableHead, ...names],
          endHeading: END_HEADING,
          rows: data.panels.map((panel) => ({
            label: panel.tableLabel,
            cells: panel.texts,
            end: rowTrace(panel.trace, panel.tableLabel, data.title),
          })),
        }}
      />
    </ChartCard>
  );
}
