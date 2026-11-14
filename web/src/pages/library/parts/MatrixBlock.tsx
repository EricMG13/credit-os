import type { RecordBlock } from "../slice";
import { TableCard } from "./TableCard";
import { TraceControl } from "./TraceControl";

/**
 * The risk matrix (C7). Its Chart side, the heat grid, is not drawn: the kit has no such chart, so
 * the Table side stands alone in the table card, with its trace control for the block and one per risk.
 */
export function MatrixBlock({ block }: { block: Extract<RecordBlock, { kind: "matrix" }> }) {
  return (
    <TableCard
      title={block.title}
      note={block.note}
      label="Table side of the risk matrix"
      size="text-h3"
      trace={{ key: block.trace, label: "Show sources for the risk matrix" }}
      head={block.columns.slice()}
      endHeading="Sources"
      rows={block.rows.map((row) => ({
        label: row.risk,
        cells: [row.probability, row.impact],
        end: <TraceControl trace={row.trace} label="Show sources for this risk" />,
      }))}
    />
  );
}
