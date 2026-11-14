import type { Changes } from "../slice";
import { TableCard } from "./TableCard";
import { TraceControl } from "./TraceControl";
import { toTableCell } from "./chartCell";

/** The Table side of the Changes presentation, earlier against current: this page's one toggle is Cards or Table. */
export function ChangesTable({ data }: { data: Extract<Changes, { kind: "compared" }> }) {
  return (
    <TableCard
      title="Earlier against current"
      note={data.tableNote}
      label="Table side of the presentation"
      size="text-h4"
      trace={null}
      head={["Change", data.earlierLabel, data.currentLabel]}
      endHeading="Sources"
      rows={data.changes.map((change) => ({
        label: change.measure,
        cells: [toTableCell(change.from), toTableCell(change.current)],
        end: <TraceControl trace={change.trace} label="Show sources for this change" />,
      }))}
    />
  );
}
