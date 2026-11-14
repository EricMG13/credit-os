import type { CHART_TABLE_LIMITS, RecordBlock } from "../slice";

type ChartTable = Extract<RecordBlock, { kind: "chartTable" }>;

/**
 * The kit's table right-aligns every column after the first and takes no property for a left one or
 * a heavier row. Tailwind builds only class names it finds written out, so each column and row the
 * reader allows (`CHART_TABLE_LIMITS`) has its own literal below.
 */
const LEFT = [
  "",
  "[&_tr>:nth-child(2)]:text-left",
  "[&_tr>:nth-child(3)]:text-left",
  "[&_tr>:nth-child(4)]:text-left",
  "[&_tr>:nth-child(5)]:text-left",
  "[&_tr>:nth-child(6)]:text-left",
  "[&_tr>:nth-child(7)]:text-left",
  "[&_tr>:nth-child(8)]:text-left",
] as const satisfies { length: typeof CHART_TABLE_LIMITS.columns };

/** A row's cells at semibold, "n.a." and the badges inside it at their own weight. */
const HEAVY = [
  "[&_tbody_tr:nth-child(1)>*]:font-semibold [&_tbody_tr:nth-child(1)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(2)>*]:font-semibold [&_tbody_tr:nth-child(2)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(3)>*]:font-semibold [&_tbody_tr:nth-child(3)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(4)>*]:font-semibold [&_tbody_tr:nth-child(4)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(5)>*]:font-semibold [&_tbody_tr:nth-child(5)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(6)>*]:font-semibold [&_tbody_tr:nth-child(6)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(7)>*]:font-semibold [&_tbody_tr:nth-child(7)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(8)>*]:font-semibold [&_tbody_tr:nth-child(8)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(9)>*]:font-semibold [&_tbody_tr:nth-child(9)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(10)>*]:font-semibold [&_tbody_tr:nth-child(10)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(11)>*]:font-semibold [&_tbody_tr:nth-child(11)_[aria-hidden=true]]:font-normal",
  "[&_tbody_tr:nth-child(12)>*]:font-semibold [&_tbody_tr:nth-child(12)_[aria-hidden=true]]:font-normal",
] as const satisfies { length: typeof CHART_TABLE_LIMITS.rows };

function classAt(classes: readonly string[], index: number): string {
  const found = classes[index];
  if (found === undefined) throw new RangeError(`no class for position ${String(index)}`);
  return found;
}

/** The classes for the table's wrapper: the left columns, then the emphasised rows. */
export function chartTableClasses(block: ChartTable): string {
  const left = block.columns.flatMap((column, index) =>
    column.align === "left" ? [classAt(LEFT, index)] : [],
  );
  const heavy = block.rows.flatMap((row, index) => (row.emphasis ? [classAt(HEAVY, index)] : []));
  return [...left, ...heavy].join(" ");
}
