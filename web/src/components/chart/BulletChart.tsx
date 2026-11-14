import type { ReactNode } from "react";
import { Missing } from "@/components/gap/Missing";
import {
  RowChart,
  checkAxis,
  colorAt,
  checkRowTable,
  pct,
  seriesColors,
  type RowTable,
} from "./RowChart";

export interface BulletRow {
  label: string;
  /** The exact text under the label: the level that matters. */
  sub: string;
  /** Position only, from zero; null draws no bar. */
  value: number | null;
  /** Position only; the dashed line stays when the value is missing. */
  target: number;
  axisMax: number;
  /** The exact text; null exactly where the value is missing. */
  text: string | null;
}

interface BulletChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  rows: BulletRow[];
  table: RowTable;
}

function check({ rows, table }: Pick<BulletChartProps, "rows" | "table">) {
  if (rows.length === 0) throw new Error("rows must not be empty");
  for (const r of rows) {
    // Bars start at one zero baseline, so every position must lie between zero and the axis max.
    checkAxis(r.label, 0, r.axisMax, [r.value, r.target]);
    if (r.value === null && r.text !== null) {
      throw new Error(`row "${r.label}": a missing value takes no text`);
    }
    if (r.value !== null && (r.text === null || r.text === "")) {
      throw new Error(`row "${r.label}": a present value needs a text`);
    }
  }
  checkRowTable(
    rows.map((r) => r.label),
    table,
  );
}

/** One row per measure: a bar from zero to the value against a dashed line at the level that matters. */
export function BulletChart({ rows, table, ...frame }: BulletChartProps) {
  check({ rows, table });
  const color = colorAt(seriesColors(["value"]), 0);
  return (
    <RowChart
      {...frame}
      table={table}
      rows={rows.map((r) => {
        const width = r.value === null ? 0 : pct(r.value, 0, r.axisMax);
        const at = pct(r.target, 0, r.axisMax);
        return {
          label: r.label,
          sub: r.sub,
          track: (
            <>
              {r.value === null ? (
                <span data-missing="" className="text-caption font-medium leading-7">
                  <Missing />
                </span>
              ) : (
                <i
                  data-bar=""
                  data-width={width}
                  className="absolute inset-y-0 left-0 min-w-0.5 rounded-ds-xs"
                  style={{ width: `${String(width)}%`, backgroundColor: color }}
                />
              )}
              <i
                data-target=""
                data-left={at}
                className="absolute -inset-y-1.5 border-l-2 border-dashed border-text-primary"
                style={{ left: `${String(at)}%` }}
              />
            </>
          ),
          values:
            r.text === null ? (
              <span data-missing="">
                <Missing />
              </span>
            ) : (
              <span data-value="">{r.text}</span>
            ),
        };
      })}
    />
  );
}
