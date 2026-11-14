import type { ReactNode } from "react";
import { Missing } from "@/components/gap/Missing";
import { Withheld } from "@/components/gap/Withheld";
import { GapBadge } from "@/components/status/StatusBadge";

/** A string is drawn as given; null is missing; the two objects are the kit's withheld and gap forms. */
export type TableCell = string | null | { withheld: true } | { gap: true };

export interface TableRowData {
  label: string;
  cells: TableCell[];
  /** A last cell for one control per row; the column exists only when some row has one. */
  end?: ReactNode;
}

interface ChartTableProps {
  /** The table's name for a screen reader. */
  caption: string;
  /** The first entry heads the row-label column. */
  head: string[];
  rows: TableRowData[];
}

function check({ head, rows }: Pick<ChartTableProps, "head" | "rows">) {
  const bad = rows.find((r) => r.cells.length !== head.length - 1);
  if (bad !== undefined) {
    throw new Error(
      `row "${bad.label}" must have ${String(head.length - 1)} cells, one per column after the label`,
    );
  }
}

function Cell({ cell }: { cell: TableCell }) {
  if (cell === null) return <Missing />;
  if (typeof cell === "string") return <>{cell}</>;
  if ("withheld" in cell) {
    return (
      <div className="flex justify-end">
        <Withheld />
      </div>
    );
  }
  return (
    <div className="flex justify-end">
      <GapBadge />
    </div>
  );
}

/** The Table side every chart kind shares: the same data as the chart, one row per series or part. */
export function ChartTable({ caption, head, rows }: ChartTableProps) {
  check({ head, rows });
  const hasEnd = rows.some((r) => r.end !== undefined);
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-body">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b-2 border-border-hairline">
            {head.map((h, i) => (
              <th
                key={i}
                scope="col"
                className={`px-3 py-2 font-medium whitespace-nowrap ${i === 0 ? "text-left" : "text-right"}`}
              >
                {h}
              </th>
            ))}
            {hasEnd ? (
              <td className="w-9 py-2 pl-2">
                <span className="sr-only">Sources</span>
              </td>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-b border-border-hairline">
              <th scope="row" className="px-3 py-2 text-left font-medium">
                {row.label}
              </th>
              {row.cells.map((cell, i) => (
                <td key={i} className="px-3 py-2 text-right tabular-nums whitespace-nowrap">
                  <Cell cell={cell} />
                </td>
              ))}
              {hasEnd ? <td className="w-9 py-2 pl-2">{row.end}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
