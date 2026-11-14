import type { ReactNode } from "react";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";
import { assignSeries } from "./series";

/** A position along an axis, as a percentage; position arithmetic only. */
export function pct(value: number, min: number, max: number): number {
  return ((value - min) / (max - min)) * 100;
}

/** The colour token of each name, by position in the series palette. */
export function seriesColors(names: string[]): string[] {
  const styles = assignSeries(names);
  return names.map((n) => {
    const style = styles.get(n);
    if (style === undefined) throw new Error(`no series style for "${n}"`);
    return style.color;
  });
}

export function colorAt(colors: string[], i: number): string {
  const c = colors[i];
  if (c === undefined) throw new Error(`no series colour at position ${String(i)}`);
  return c;
}

export function checkAxis(label: string, min: number, max: number, values: (number | null)[]) {
  if (!(max > min)) throw new Error(`row "${label}": the axis max must be above its min`);
  for (const v of values) {
    if (v !== null && !(v >= min && v <= max)) {
      throw new Error(`row "${label}": a position is outside the axis`);
    }
  }
}

export interface RowTable {
  head: string[];
  rows: TableRowData[];
  endHeading?: string;
}

/** The table's rows are the chart's rows: same labels, same order. */
export function checkRowTable(labels: string[], table: RowTable) {
  const repeated = labels.find((l, i) => labels.indexOf(l) !== i);
  if (repeated !== undefined) throw new Error(`row labels must be distinct: "${repeated}" repeats`);
  if (table.rows.length !== labels.length || table.rows.some((r, i) => r.label !== labels[i])) {
    throw new Error("the table must have one row per chart row, with the same labels, in order");
  }
}

interface RowSpec {
  label: string;
  sub?: string;
  /** The positioned marks; the cell is `relative`, 28px high. */
  track: ReactNode;
  /** The row's value texts, drawn right-aligned. */
  values: ReactNode;
}

interface RowChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  rows: RowSpec[];
  legend?: ReactNode;
  table: RowTable;
}

/** The layout the row kinds share: label and sub-label, a track, the value text. No focus stop. */
export function RowChart({
  title,
  as,
  note,
  subtitle,
  actions,
  rows,
  legend,
  table,
}: RowChartProps) {
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <div className="flex flex-col gap-5">
            <div className="grid grid-cols-[minmax(120px,1fr)_minmax(0,1.6fr)_minmax(72px,auto)] items-center gap-x-5 gap-y-4 text-small">
              {rows.map((r) => (
                <div key={r.label} data-row="" className="contents">
                  <div>
                    <b className="block font-medium text-text-primary">{r.label}</b>
                    {r.sub === undefined ? null : (
                      <span data-sub="" className="text-caption text-text-tertiary">
                        {r.sub}
                      </span>
                    )}
                  </div>
                  <div className="relative h-7">{r.track}</div>
                  <div className="flex flex-col text-right font-medium tabular-nums text-text-primary">
                    {r.values}
                  </div>
                </div>
              ))}
            </div>
            {legend}
          </div>
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

/** A legend: each entry is a swatch drawn by the caller and its label. */
export function RowLegend({ items }: { items: { label: string; swatch: ReactNode }[] }) {
  return (
    <ul aria-label="Legend" className="flex flex-wrap gap-x-5 gap-y-2">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-2 text-small text-text-secondary">
          <span aria-hidden="true" className="flex items-center">
            {i.swatch}
          </span>
          {i.label}
        </li>
      ))}
    </ul>
  );
}
