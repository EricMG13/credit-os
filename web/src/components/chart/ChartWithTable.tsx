import type { ReactNode } from "react";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";

interface ChartWithTableProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** The chart form; it is drawn while the Chart side of the toggle is shown. */
  chart: ReactNode;
  /** The table form of the same data, drawn while the Table side is shown. */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

/** The titled frame whose Chart side draws `chart` and whose Table side draws `table`. */
export function ChartWithTable({
  title,
  as,
  note,
  subtitle,
  actions,
  chart,
  table,
}: ChartWithTableProps) {
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          chart
        ) : (
          <ChartTable
            caption={title}
            head={table.head}
            rows={table.rows}
            endHeading={table.endHeading}
          />
        )
      }
    </ChartFrame>
  );
}
