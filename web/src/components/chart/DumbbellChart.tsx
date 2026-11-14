import type { ReactNode } from "react";
import { Missing } from "@/components/gap/Missing";
import {
  RowChart,
  RowLegend,
  checkAxis,
  checkRowTable,
  colorAt,
  pct,
  seriesColors,
  type RowTable,
} from "./RowChart";

export interface DumbbellRow {
  label: string;
  /** The earlier value, position only; null draws no mark. */
  from: number | null;
  /** The later value, position only; null draws no mark. */
  to: number | null;
  /** The exact text of both values, "n.a." included where one is missing. */
  text: string;
}

interface DumbbellChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** The earlier and the later period, as the legend names them. */
  names: [string, string];
  /** One axis for every row. */
  axis: { min: number; max: number };
  rows: DumbbellRow[];
  table: RowTable;
}

function check({ rows, axis, table }: Pick<DumbbellChartProps, "rows" | "axis" | "table">) {
  if (rows.length === 0) throw new Error("rows must not be empty");
  for (const r of rows) {
    checkAxis(r.label, axis.min, axis.max, [r.from, r.to]);
    if (r.from === null && r.to === null) {
      throw new Error(`row "${r.label}": both values are missing, so there is nothing to draw`);
    }
    if (r.text === "") throw new Error(`row "${r.label}": the row needs a text`);
  }
  checkRowTable(
    rows.map((r) => r.label),
    table,
  );
}

const MARK = "absolute top-[9px] -ml-[5px] size-2.5";

/** One row per segment: an earlier ring joined to a later filled mark on one shared axis. */
export function DumbbellChart({ names, axis, rows, table, ...frame }: DumbbellChartProps) {
  check({ rows, axis, table });
  // The later period takes the first series style and the earlier the second, as the mock does.
  const colors = seriesColors([names[1], names[0]]);
  const laterColor = colorAt(colors, 0);
  const earlierColor = colorAt(colors, 1);
  return (
    <RowChart
      {...frame}
      table={table}
      rows={rows.map((r) => {
        const from = r.from === null ? null : pct(r.from, axis.min, axis.max);
        const to = r.to === null ? null : pct(r.to, axis.min, axis.max);
        return {
          label: r.label,
          track: (
            <>
              {from === null || to === null ? (
                <span
                  data-missing=""
                  className="absolute top-1 left-[12%] -translate-x-1/2 text-caption font-medium"
                >
                  <Missing />
                </span>
              ) : (
                <i
                  data-line=""
                  data-left={Math.min(from, to)}
                  data-width={Math.abs(to - from)}
                  className="absolute top-[13px] h-0.5 bg-border-control"
                  style={{
                    left: `${String(Math.min(from, to))}%`,
                    width: `${String(Math.abs(to - from))}%`,
                  }}
                />
              )}
              {from === null ? null : (
                <i
                  data-mark="from"
                  data-left={from}
                  className={`${MARK} rounded-[1px] bg-surface-card`}
                  style={{
                    left: `${String(from)}%`,
                    boxShadow: `inset 0 0 0 2px ${earlierColor}`,
                  }}
                />
              )}
              {to === null ? null : (
                <i
                  data-mark="to"
                  data-left={to}
                  className={`${MARK} rounded-full`}
                  style={{ left: `${String(to)}%`, backgroundColor: laterColor }}
                />
              )}
            </>
          ),
          values: <span data-value="">{r.text}</span>,
        };
      })}
      legend={
        <RowLegend
          items={[
            {
              label: names[0],
              swatch: (
                <i
                  className="size-2.5 rounded-[1px]"
                  style={{ boxShadow: `inset 0 0 0 2px ${earlierColor}` }}
                />
              ),
            },
            {
              label: names[1],
              swatch: (
                <i className="size-2.5 rounded-full" style={{ backgroundColor: laterColor }} />
              ),
            },
          ]}
        />
      }
    />
  );
}
