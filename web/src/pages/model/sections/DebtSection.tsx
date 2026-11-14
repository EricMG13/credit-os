import { StackChart } from "@/components/chart/StackChart";
import type { ColumnsData, Stack } from "../slice/types";
import { ColumnsCard } from "./ColumnsCard";
import { ChartCard, END_HEADING, SectionHeading, chartTrace, rowTrace } from "./shared";

/** Debt by instrument and maturities by year; each card takes the whole row. */
export function DebtSection({ stack, maturities }: { stack: Stack; maturities: ColumnsData }) {
  return (
    <section className="flex flex-col gap-4">
      <SectionHeading>Debt</SectionHeading>
      <div className="flex flex-col gap-6">
        <ChartCard>
          <StackChart
            title={stack.title}
            as="h3"
            subtitle={stack.subtitle}
            note={stack.note}
            actions={chartTrace(stack.trace, stack.title)}
            parts={stack.parts}
            table={{
              head: stack.head,
              endHeading: END_HEADING,
              rows: stack.parts.map((part) => ({
                label: part.name,
                cells: [part.text, part.share],
                end: rowTrace(part.trace, part.name, stack.title),
              })),
            }}
          />
        </ChartCard>
        <ColumnsCard data={maturities} />
      </div>
    </section>
  );
}
