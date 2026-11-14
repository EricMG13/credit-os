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

export interface RangeRow {
  label: string;
  /** The exact text of the range, shown under the label. */
  rangeText: string;
  /** Position only; null draws no strip. */
  range: { low: number; high: number } | null;
  /** Position and exact text of each case; both null exactly where the value is missing. */
  markers: { name: string; value: number | null; text: string | null }[];
  axis: { min: number; max: number };
}

interface RangeStripChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** The legend's label for the strip. */
  rangeLabel: string;
  rows: RangeRow[];
  table: RowTable;
  /** Which marker (by position) stands out by weight: wider and taller. None when absent. */
  emphasised?: number;
}

/** Throws on inconsistent props; returns the marker names every row shares. */
function check({
  rows,
  table,
  emphasised,
}: Pick<RangeStripChartProps, "rows" | "table" | "emphasised">): string[] {
  const first = rows[0];
  if (first === undefined) throw new Error("rows must not be empty");
  if (first.markers.length === 0) throw new Error("rows need at least one marker");
  const names = first.markers.map((m) => m.name);
  if (emphasised !== undefined && !(emphasised >= 0 && emphasised < names.length)) {
    throw new Error(
      `emphasised ${String(emphasised)} is not one of the ${String(names.length)} markers`,
    );
  }
  for (const r of rows) {
    if (r.markers.map((m) => m.name).join("\u0000") !== names.join("\u0000")) {
      throw new Error(`row "${r.label}": the markers must be the same names, in the same order`);
    }
    if (r.range !== null && !(r.range.low <= r.range.high)) {
      throw new Error(`row "${r.label}": the range's low must not be above its high`);
    }
    checkAxis(r.label, r.axis.min, r.axis.max, [
      r.range?.low ?? null,
      r.range?.high ?? null,
      ...r.markers.map((m) => m.value),
    ]);
    for (const m of r.markers) {
      if (m.value === null && m.text !== null) {
        throw new Error(`row "${r.label}", ${m.name}: a missing value takes no text`);
      }
      if (m.value !== null && (m.text === null || m.text === "")) {
        throw new Error(`row "${r.label}", ${m.name}: a present value needs a text`);
      }
    }
  }
  checkRowTable(
    rows.map((r) => r.label),
    table,
  );
  return names;
}

/** The mock's 2px ring in the card surface keeps a marker readable over the strip. */
const MARKER = "absolute -ml-0.5 rounded-sm ring-2 ring-surface-card";

function Track({
  row: r,
  colors,
  emphasised,
}: {
  row: RangeRow;
  colors: string[];
  emphasised: number | undefined;
}) {
  if (r.range === null) return null;
  const left = pct(r.range.low, r.axis.min, r.axis.max);
  const width = pct(r.range.high, r.axis.min, r.axis.max) - left;
  return (
    <>
      <i
        data-range=""
        data-left={left}
        data-width={width}
        className="absolute top-2 h-3 rounded-ds-xs bg-action-subtle-hover"
        style={{ left: `${String(left)}%`, width: `${String(width)}%` }}
      />
      {r.markers.map((m, i) => {
        if (m.value === null) return null;
        const at = pct(m.value, r.axis.min, r.axis.max);
        return (
          <i
            key={m.name}
            data-marker=""
            data-name={m.name}
            data-left={at}
            className={
              i === emphasised
                ? "absolute top-0 -ml-0.75 h-7 w-1.5 rounded-sm ring-2 ring-surface-card"
                : `${MARKER} top-0.5 h-6 w-1`
            }
            style={{ left: `${String(at)}%`, backgroundColor: colorAt(colors, i) }}
          />
        );
      })}
    </>
  );
}

/** One row per measure: a range strip with a tick for each case, each on its own axis. */
export function RangeStripChart({
  rangeLabel,
  rows,
  table,
  emphasised,
  ...frame
}: RangeStripChartProps) {
  const names = check({ rows, table, emphasised });
  const colors = seriesColors(names);
  return (
    <RowChart
      {...frame}
      table={table}
      rows={rows.map((r) => ({
        label: r.label,
        sub: r.rangeText,
        track: <Track row={r} colors={colors} emphasised={emphasised} />,
        values: r.markers.map((m, i) => (
          <span
            key={m.name}
            data-value=""
            className={`flex items-center justify-end gap-1.5${
              emphasised !== undefined && i !== emphasised ? " text-text-tertiary" : ""
            }`}
          >
            {r.markers.length >= 2 && m.value !== null ? (
              <i
                aria-hidden="true"
                className="h-3 w-1 rounded-sm"
                style={{ backgroundColor: colorAt(colors, i) }}
              />
            ) : null}
            {m.text === null ? (
              <span data-missing="">
                <Missing />
              </span>
            ) : (
              m.text
            )}
          </span>
        )),
      }))}
      legend={
        <RowLegend
          items={[
            {
              label: rangeLabel,
              swatch: <i className="h-3 w-[18px] rounded-ds-xs bg-action-subtle-hover" />,
            },
            ...names.map((n, i) => ({
              label: n,
              swatch: (
                <i
                  className="h-3.5 w-1 rounded-sm"
                  style={{ backgroundColor: colorAt(colors, i) }}
                />
              ),
            })),
          ]}
        />
      }
    />
  );
}
