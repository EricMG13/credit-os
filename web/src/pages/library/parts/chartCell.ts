import type { TableCell } from "@/components/chart/ChartTable";
import type { Cell } from "../slice";

/**
 * A slice figure as the shared Table side takes it: the exact text, `null` for missing, or the
 * withheld and gap forms. The reader has already refused a blank text, which the table rejects.
 */
export function toTableCell(cell: Cell): TableCell {
  if (cell === null) return null;
  switch (cell.kind) {
    case "value":
      return cell.text;
    case "withheld":
      return { withheld: true };
    case "gap":
      return { gap: true };
  }
}
