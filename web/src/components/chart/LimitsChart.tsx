import type { ReactNode } from "react";
import { Missing } from "@/components/gap/Missing";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";
import { assignSeries } from "./series";

export interface LimitColumn {
  label: string;
  /** Position only; null is missing. */
  exposure: number | null;
  /** Position only; null is missing. */
  limit: number | null;
  /** The column's own axis maximum, delivered: a bar and a tick sit at their value over it. */
  scaleMax: number;
  /** The exact exposure as drawn; null exactly where the exposure is missing. */
  exposureText: string | null;
  /** The exact limit as drawn, with its word ("limit 3.0%"); null exactly where the limit is missing. */
  limitText: string | null;
}

interface LimitsChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  columns: LimitColumn[];
  /** One row per column, in order: the exposure, then the limit without its word ("3.0%"). */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

function pair(c: LimitColumn, what: "exposure" | "limit") {
  const value = c[what];
  const text = c[what === "exposure" ? "exposureText" : "limitText"];
  if (value === null) {
    if (text !== null) throw new Error(`column "${c.label}": a missing ${what} takes no text`);
    return;
  }
  if (text === null) throw new Error(`column "${c.label}": a present ${what} needs a text`);
  if (!(value >= 0)) {
    throw new Error(
      `column "${c.label}": values sit on one zero baseline, so ${what} must be zero or more`,
    );
  }
  if (value > c.scaleMax) throw new Error(`column "${c.label}": the ${what} is above the scale`);
}

function check({ columns, table }: Pick<LimitsChartProps, "columns" | "table">) {
  if (columns.length === 0) throw new Error("limits need at least one column");
  const repeated = columns.find((c, i) => columns.findIndex((o) => o.label === c.label) !== i);
  if (repeated !== undefined) {
    throw new Error(`column labels must be distinct: "${repeated.label}" repeats`);
  }
  for (const c of columns) {
    if (!(c.scaleMax > 0)) throw new Error(`column "${c.label}": the scale must be more than zero`);
    pair(c, "exposure");
    pair(c, "limit");
  }
  if (table.head.length !== 3)
    throw new Error("the table must have an exposure and a limit column");
  if (
    table.rows.map((r) => r.label).join("\u0000") !== columns.map((c) => c.label).join("\u0000")
  ) {
    throw new Error("the table must have one row per column, labelled with the column, in order");
  }
  columns.forEach((c, i) => {
    const cells = table.rows[i]?.cells ?? [];
    const limit = cells[1];
    // A missing cell is never read as an empty word: a drawn limit needs the cell's own text.
    const limitOk =
      c.limitText === null
        ? limit === null
        : typeof limit === "string" && c.limitText === `limit ${limit}`;
    if (cells.length !== 2 || cells[0] !== c.exposureText || !limitOk) {
      throw new Error(`column "${c.label}": the table's cells must be the column's texts`);
    }
  });
}

/** The mock's place for "limit n.a." (86% of the track), and the tallest bar that leaves it clear. */
const NO_LIMIT_AT = 86;
const NO_LIMIT_CLEAR_BELOW = 77;

/**
 * The track is 240px (the plot's 276px less 36px of headroom). The exposure label takes 4px to
 * 20px above the bar top and the limit label 2px to 18px above the tick, so the two overlap, or
 * the dashed line strikes the exposure text, when the tick is less than 18px above the bar top or
 * less than 14px below it. Then both labels stack above the higher mark.
 */
const TRACK_PX = 240;
const CLASH_ABOVE_PX = 18;
const CLASH_BELOW_PX = 14;

const TEXT = "whitespace-nowrap text-xs font-medium leading-4";

function Column({ c, color }: { c: LimitColumn; color: string }) {
  const height = c.exposure === null ? null : (c.exposure / c.scaleMax) * 100;
  const at = c.limit === null ? null : (c.limit / c.scaleMax) * 100;
  // The column's top padding is the headroom for the two stacked label lines (2 x 16px and a 4px
  // gap), so a bar near its scale maximum keeps them inside the plot.
  // "limit n.a." stands at the mock's 86% of the track, as a limit label would, unless the bar's
  // exposure label would reach it (a bar above NO_LIMIT_CLEAR_BELOW); then it stacks with that
  // label above the bar's top, so no two labels overlap. With no exposure it stacks with "n.a.".
  const missingNote = (
    <span data-limit-missing="" className={`${TEXT} text-text-secondary`}>
      limit <Missing />
    </span>
  );
  const stacked = at === null && (height === null || height > NO_LIMIT_CLEAR_BELOW);
  // Position arithmetic on the delivered positions: the tick's height above the bar top, in px.
  const gap =
    c.exposure === null || c.limit === null
      ? null
      : (c.limit - c.exposure) * (TRACK_PX / c.scaleMax);
  const clash = gap !== null && gap < CLASH_ABOVE_PX && gap > -CLASH_BELOW_PX;
  const barIsHigher = gap !== null && gap <= 0;
  const limitLabel = (
    <span data-limit-label="" className="text-text-secondary">
      {c.limitText}
    </span>
  );
  // With no exposure, "n.a." stands on the baseline: a tick under the limit label's height (18px)
  // would put its label over it, so the label stacks above "n.a." instead.
  const limitOverNa = height === null && at !== null && at < (CLASH_ABOVE_PX / TRACK_PX) * 100;
  const noLimit = stacked ? missingNote : clash && barIsHigher ? limitLabel : null;
  return (
    <div data-column={c.label} className="relative flex flex-1 flex-col pt-9">
      <div data-track="" className="relative flex flex-1 items-end justify-center">
        {height === null ? (
          <span
            data-missing=""
            className={`${TEXT} flex flex-col items-center pb-1 text-text-tertiary`}
          >
            {limitOverNa ? limitLabel : null}
            <Missing />
            {noLimit}
          </span>
        ) : (
          <div
            data-bar=""
            data-height={height}
            className="relative min-h-0.5 w-14 max-w-3/5 rounded-t-[6px]"
            style={{ height: `${String(height)}%`, backgroundColor: color }}
          >
            {clash && !barIsHigher ? null : (
              <span
                className={`${TEXT} absolute bottom-full left-1/2 flex -translate-x-1/2 flex-col items-center pb-1 text-text-primary`}
              >
                {noLimit}
                <span data-exposure="">{c.exposureText}</span>
              </span>
            )}
          </div>
        )}
        {at === null && !stacked ? (
          <div
            data-limit-at={NO_LIMIT_AT}
            className="absolute inset-x-[14%]"
            style={{ bottom: `${String(NO_LIMIT_AT)}%` }}
          >
            <span className="absolute bottom-0.5 right-0">{missingNote}</span>
          </div>
        ) : null}
        {at === null ? null : (
          <div
            data-tick=""
            data-at={at}
            className="absolute inset-x-[14%] border-t-2 border-dashed border-text-primary"
            style={{ bottom: `${String(at)}%` }}
          >
            {limitOverNa ? null : clash ? (
              barIsHigher ? null : (
                <span
                  className={`${TEXT} absolute bottom-1 left-1/2 flex -translate-x-1/2 flex-col items-center text-text-primary`}
                >
                  {limitLabel}
                  <span data-exposure="">{c.exposureText}</span>
                </span>
              )
            ) : (
              <span className={`${TEXT} absolute bottom-0.5 right-0`}>{limitLabel}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Vertical columns, each on its own scale, with a dashed tick at its limit. */
export function LimitsChart({
  title,
  as,
  note,
  subtitle,
  actions,
  columns,
  table,
}: LimitsChartProps) {
  check({ columns, table });
  const color = assignSeries(["exposure"]).get("exposure")?.color;
  if (color === undefined) throw new Error("the series palette has no first style");
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <div className="flex flex-col">
            <div data-plot="" className="flex h-[276px] border-b border-border-control">
              {columns.map((c) => (
                <Column key={c.label} c={c} color={color} />
              ))}
            </div>
            <div className="flex pt-2 text-xs text-text-tertiary">
              {columns.map((c) => (
                <span key={c.label} className="flex-1 px-0.5 text-center">
                  {c.label}
                </span>
              ))}
            </div>
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
