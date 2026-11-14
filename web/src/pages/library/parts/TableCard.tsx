import { ChartTable, type TableRowData } from "@/components/chart/ChartTable";
import { FOCUS } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";

/**
 * A chart's Table side alone, in the card the mock draws for it: the title (a heading the module
 * navigator can focus), an optional basis note, the block's one trace control in the header, and the
 * kit's table. The kit's ChartFrame is not used where no chart side is drawn: its Chart or Table
 * toggle would have a dead side. The trace control stays in this one header slot so it can move into
 * ChartFrame's `actions` when a chart kind exists. A row's control shows while the row is hovered.
 */
export function TableCard({
  title,
  note,
  label,
  size,
  trace,
  head,
  rows,
  endHeading,
}: {
  title: string;
  note: string | null;
  /** The card's name as a region. */
  label: string;
  size: "text-h3" | "text-h4";
  /** The block's own trace control: its key and accessible name; `null` draws none. */
  trace: { key: string | null; label: string } | null;
  head: string[];
  rows: TableRowData[];
  endHeading: string;
}) {
  const Heading = SUBSECTION_HEADING;
  return (
    <section
      aria-label={label}
      className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-surface-card p-5 shadow-xs"
    >
      <div className={`${TRACE_HOST} flex items-start justify-between gap-3`}>
        <div>
          <Heading tabIndex={-1} className={`font-display ${size} text-text-primary ${FOCUS}`}>
            {title}
          </Heading>
          {note === null ? null : <p className="text-small text-text-tertiary">{note}</p>}
        </div>
        {trace === null ? null : <TraceControl trace={trace.key} label={trace.label} />}
      </div>
      <div className="[&_tbody_tr:hover_button]:opacity-100">
        <ChartTable caption={title} head={head} rows={rows} endHeading={endHeading} />
      </div>
    </section>
  );
}
