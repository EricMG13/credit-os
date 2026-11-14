import { Badge } from "@/components/base/badges/badges";
import { ChartTable, type TableRowData } from "@/components/chart/ChartTable";
import { FOCUS } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";

/**
 * A chart's Table side alone, in the card the mock draws for it: the title (a heading the module
 * navigator can focus), an optional basis note, the block's one trace control in the header, and the
 * kit's table, then any footnotes. The kit's ChartFrame is not used where no chart side is drawn: its Chart or Table
 * toggle would have a dead side. The trace control stays in this one header slot so it can move into
 * ChartFrame's `actions` when a chart kind exists. A row's control shows while the row is hovered.
 */
export function TableCard({
  title,
  count,
  note,
  label,
  size,
  trace,
  head,
  rows,
  endHeading,
  footnotes = [],
  tableClass = "",
}: {
  title: string;
  /** The delivered count beside the title (a register's rows), or `null`. */
  count?: string | null;
  note: string | null;
  /** The card's name as a region. */
  label: string;
  size: "text-h3" | "text-h4";
  /** The block's own trace control: its key and accessible name; `null` draws none. */
  trace: { key: string | null; label: string } | null;
  head: string[];
  rows: TableRowData[];
  /** The heading of the end column, needed only where a row has an end control. */
  endHeading?: string;
  /** Sentences under the table, in the order delivered. */
  footnotes?: readonly string[];
  /** Classes on the table's wrapper, for what the kit's table takes no property for. */
  tableClass?: string;
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
            {count == null ? null : (
              <>
                {" "}
                <Badge size="sm" color="gray">
                  {count}
                </Badge>
              </>
            )}
          </Heading>
          {note === null ? null : <p className="text-small text-text-tertiary">{note}</p>}
        </div>
        {trace === null ? null : <TraceControl trace={trace.key} label={trace.label} />}
      </div>
      <div className={`[&_tbody_tr:hover_button]:opacity-100 ${tableClass}`}>
        <ChartTable caption={title} head={head} rows={rows} endHeading={endHeading} />
      </div>
      {footnotes.map((text) => (
        <p key={text} className="text-small text-text-tertiary">
          {text}
        </p>
      ))}
    </section>
  );
}
