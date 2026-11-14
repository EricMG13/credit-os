import type { ReactNode } from "react";
import { Missing } from "@/components/gap/Missing";
import { BarLegend } from "./ColumnsChart";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";
import { assignSeries, type SeriesStyle } from "./series";

export interface ComparisonPanel {
  measure: string;
  /** The panel's own axis maximum, delivered; a bar's width is its value over it. */
  max: number;
  /** Position only, in case order; null is missing. */
  values: [number | null, number | null];
  /** The exact text of each value; null exactly where the value is missing. */
  texts: [string | null, string | null];
}

interface ComparisonChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** The two cases' names, as the legend shows them. */
  cases: [string, string];
  /** The names beside each bar when shorter than the cases' names; the cases' names otherwise. */
  rowLabels?: [string, string];
  panels: ComparisonPanel[];
  /** One row per panel, in order, with one cell per case; its labels may be shorter than the measures. */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

function check({ cases, panels, table }: Pick<ComparisonChartProps, "cases" | "panels" | "table">) {
  const repeated = panels.find((p, i) => panels.findIndex((o) => o.measure === p.measure) !== i);
  if (repeated !== undefined) {
    throw new Error(`panel measures must be distinct: "${repeated.measure}" repeats`);
  }
  if (cases[0] === cases[1]) throw new Error("the two cases must have distinct names");
  for (const p of panels) {
    if (!(p.max > 0)) throw new Error(`panel "${p.measure}": max must be more than zero`);
    p.values.forEach((v, i) => {
      const text = p.texts[i];
      if (v === null) {
        if (text !== null) {
          throw new Error(`panel "${p.measure}", ${cases[i] ?? ""}: a missing value takes no text`);
        }
        return;
      }
      if (text === null || text === undefined) {
        throw new Error(`panel "${p.measure}", ${cases[i] ?? ""}: a present value needs a text`);
      }
      if (!(v >= 0)) {
        throw new Error(
          `panel "${p.measure}": values sit on one zero baseline, so they must be zero or more`,
        );
      }
      if (v > p.max) throw new Error(`panel "${p.measure}": a value is above the panel's max`);
    });
  }
  if (table.head.slice(1).join("\u0000") !== cases.join("\u0000")) {
    throw new Error("table columns after the first must be the cases, in order");
  }
  if (table.rows.length !== panels.length) {
    throw new Error("the table must have one row per panel, in order");
  }
  panels.forEach((p, i) => {
    const cells = table.rows[i]?.cells ?? [];
    if (cells.length !== 2 || cells[0] !== p.texts[0] || cells[1] !== p.texts[1]) {
      throw new Error(`panel "${p.measure}": the table's cells must be the panel's texts`);
    }
  });
}

function colorOf(styles: Map<string, SeriesStyle>, name: string): string {
  const style = styles.get(name);
  if (style === undefined) throw new Error(`no series style for case "${name}"`);
  return style.color;
}

function Row({
  label,
  caseName,
  color,
  value,
  max,
  text,
}: {
  label: string;
  caseName: string;
  color: string;
  value: number | null;
  max: number;
  text: string | null;
}) {
  const width = value === null ? 0 : (value / max) * 100;
  return (
    <>
      <span className="text-text-secondary">{label}</span>
      <div className="relative h-7">
        {value === null ? (
          <span data-missing="" className="text-small font-medium leading-7">
            <Missing />
          </span>
        ) : (
          <i
            data-bar=""
            data-case={caseName}
            data-width={width}
            data-zero={value === 0 ? "" : undefined}
            className="absolute inset-y-0 left-0 min-w-0.5 rounded-ds-xs"
            style={{ width: `${String(width)}%`, backgroundColor: color }}
          />
        )}
      </div>
      <span data-value="" className="text-right font-medium tabular-nums text-text-primary">
        {text ?? ""}
      </span>
    </>
  );
}

/** Small multiples: one panel per measure, each on its own scale, two bars per panel. */
export function ComparisonChart({
  title,
  as,
  note,
  subtitle,
  actions,
  cases,
  rowLabels,
  panels,
  table,
}: ComparisonChartProps) {
  check({ cases, panels, table });
  const styles = assignSeries(cases);
  const Panel = as === "h3" ? "h4" : "h5";
  const labels = rowLabels ?? cases;
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <div className="flex flex-col gap-6">
            <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,300px),1fr))] gap-x-10 gap-y-8">
              {panels.map((p) => (
                <div key={p.measure} data-panel="" className="flex min-w-0 flex-col gap-2.5">
                  <Panel className="text-small font-medium text-text-secondary">{p.measure}</Panel>
                  <div className="grid grid-cols-[72px_minmax(0,1fr)_56px] items-center gap-x-3 gap-y-2.5 text-small">
                    {cases.map((c, i) => (
                      <Row
                        key={c}
                        label={labels[i] ?? c}
                        caseName={c}
                        color={colorOf(styles, c)}
                        value={p.values[i] ?? null}
                        max={p.max}
                        text={p.texts[i] ?? null}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <BarLegend names={cases} styles={styles} centered />
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
