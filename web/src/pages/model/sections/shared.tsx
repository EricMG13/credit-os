import type { ReactNode } from "react";
import { Card } from "@/components/card/Card";
import { TraceControl } from "../parts/TraceControl";

/** The heading of the table's last column, which holds one trace control per row. */
export const END_HEADING = "Show sources";

/**
 * A chart in a card. The wrapper is the `group/trace` that shows the chart's trace control and
 * its row controls when the card is hovered or focused.
 */
export function ChartCard({ children }: { children: ReactNode }) {
  return (
    <div className="group/trace">
      <Card>{children}</Card>
    </div>
  );
}

/** The chart's own trace control, named by its title; none when the slice gives no address. */
export function chartTrace(trace: string | null, title: string): ReactNode {
  return trace === null ? undefined : (
    <TraceControl href={trace} label={`Show the sources for ${title}`} />
  );
}

/** A table row's trace control, named by the row and the chart, so no two share a name. */
export function rowTrace(trace: string | null, label: string, title: string): ReactNode {
  return trace === null ? undefined : (
    <TraceControl href={trace} label={`Show the sources for ${label} (${title})`} />
  );
}

/** A section heading: an `h2` under the shell's `h1`, or the `h3` a page passes when it has its own `h2`. */
export function SectionHeading({
  children,
  as: Tag = "h2",
}: {
  children: string;
  as?: "h2" | "h3";
}) {
  return <Tag className="font-display text-h3 text-text-primary">{children}</Tag>;
}

/** Decision 0006, ruling 16: a half-width chart card takes the whole row from this many table columns. */
const WIDE_TABLE = 5;

/**
 * The grid for half-width chart cards: the mock's `.g2`, columns of at least 460px so the cards
 * stack when two would be narrower, or one column when a table side has five or more columns
 * (the label column included).
 */
export function pairGrid(tableColumns: number): string {
  return tableColumns >= WIDE_TABLE
    ? "grid grid-cols-1 gap-6"
    : "grid grid-cols-[repeat(auto-fit,minmax(min(100%,460px),1fr))] gap-6";
}
