import type { RecordBlock } from "../slice";
import { TableCard } from "./TableCard";
import { toTableCell } from "./chartCell";
import { chartTableClasses } from "./chartTableStyle";

type ChartTable = Extract<RecordBlock, { kind: "chartTable" }>;

/** The mock's accessible name of each chart's trace control. */
const TRACE_LABEL: Record<ChartTable["chart"], string> = {
  stack: "Show sources for the debt stack",
  columns: "Show sources for maturities",
  bullet: "Show sources for headroom",
  bridge: "Show sources for the liquidity walk",
  scatter: "Show sources for the peer scatter",
  range: "Show sources for the peer range",
};

/**
 * A chart's data drawn as its Table side, in a card with the title, the basis note, one trace
 * control, the table and the footnotes. The Chart side of each kind is not drawn: the kit has no
 * such chart, so there is no Chart or Table toggle. `chart` names the kind only for the control's name.
 */
export function ChartTableBlock({ block }: { block: ChartTable }) {
  return (
    <TableCard
      title={block.title}
      note={block.note}
      label={block.title}
      size="text-h4"
      trace={{ key: block.trace, label: TRACE_LABEL[block.chart] }}
      head={block.columns.map((column) => column.label)}
      rows={block.rows.map((row) => {
        const [first, ...cells] = row.cells;
        if (typeof first !== "string") throw new TypeError("a chart table row has no text label");
        return {
          label: first,
          cells: cells.map((cell) => (typeof cell === "string" ? cell : toTableCell(cell))),
        };
      })}
      footnotes={block.footnotes}
      tableClass={chartTableClasses(block)}
    />
  );
}
