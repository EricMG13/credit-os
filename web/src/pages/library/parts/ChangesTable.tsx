import { ChartTable } from "@/components/chart/ChartTable";
import type { Changes } from "../slice";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";
import { toTableCell } from "./chartCell";

/**
 * The Table side of the Changes presentation, earlier against current, in the card the mock draws
 * for it. The kit's ChartFrame is not used: it carries its own Chart or Table toggle, and this page's
 * one toggle is Cards or Table. The trace controls show with the row's hover, focus or touch.
 */
export function ChangesTable({ data }: { data: Extract<Changes, { kind: "compared" }> }) {
  const Heading = SUBSECTION_HEADING;
  return (
    <section
      aria-label="Table side of the presentation"
      className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-surface-card p-5 shadow-xs"
    >
      <div>
        <Heading className="font-display text-h4 text-text-primary">
          Earlier against current
        </Heading>
        <p className="text-small text-text-tertiary">{data.tableNote}</p>
      </div>
      <div className="[&_tbody_tr:hover_button]:opacity-100">
        <ChartTable
          caption="Earlier against current"
          head={["Change", data.earlierLabel, data.currentLabel]}
          endHeading="Sources"
          rows={data.changes.map((change) => ({
            label: change.measure,
            cells: [toTableCell(change.from), toTableCell(change.current)],
            end: (
              <span className={TRACE_HOST}>
                <TraceControl trace={change.trace} label="Show sources for this change" />
              </span>
            ),
          }))}
        />
      </div>
    </section>
  );
}
