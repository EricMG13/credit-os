import { WaterfallChart } from "@/components/chart/WaterfallChart";
import type { Bridge } from "../slice/types";
import { ChartCard, END_HEADING, SectionHeading, chartTrace, rowTrace, pairGrid } from "./shared";

const LEGEND = { total: "Total", up: "Increase (plus)", down: "Decrease (minus)" };

/** The bridges, each drawn for the chosen case; the table beside them holds both cases. */
export function Bridges({ bridges, caseIndex }: { bridges: readonly Bridge[]; caseIndex: number }) {
  return (
    <section className="flex flex-col gap-4">
      <SectionHeading>Bridges</SectionHeading>
      <div className={pairGrid(Math.max(...bridges.map((b) => b.head.length)))}>
        {bridges.map((bridge) => {
          const steps = bridge.caseSteps[caseIndex];
          if (steps === undefined) throw new Error(`no steps for case ${String(caseIndex)}`);
          return (
            <ChartCard key={bridge.title}>
              <WaterfallChart
                title={bridge.title}
                as="h3"
                subtitle={bridge.subtitle}
                note={bridge.note}
                actions={chartTrace(bridge.trace, bridge.title)}
                steps={steps}
                yTicks={bridge.yTicks}
                legend={LEGEND}
                table={{
                  head: bridge.head,
                  endHeading: END_HEADING,
                  rows: bridge.rows.map((row) => ({
                    label: row.label,
                    cells: row.cells,
                    end: rowTrace(row.trace, row.label, bridge.title),
                  })),
                }}
              />
            </ChartCard>
          );
        })}
      </div>
    </section>
  );
}
