import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type BarShapeProps,
  type TooltipContentProps,
} from "recharts";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";
import { ReadoutRow } from "./PathChart";
import { assignSeries, type SeriesStyle } from "./series";

export interface StackPart {
  name: string;
  /** Position only: the segment's length is its value over the row's total. */
  value: number;
  /** The exact amount, as drawn. */
  text: string;
  /** The exact share, as drawn; given for every part or for none. */
  share?: string;
}

interface StackChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** In rank order, as delivered. */
  parts: StackPart[];
  /** One row per part, in the same order: the amount, then the share when parts carry one. */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

const ROW_HEIGHT = 40;
const BAR = 32;
const RADIUS = 6;
/** The gap between segments, drawn by narrowing each segment but the last. */
const SEGMENT_GAP = 2;

function keyOf(i: number): string {
  return `s${String(i)}`;
}

function check({ parts, table }: Pick<StackChartProps, "parts" | "table">) {
  if (parts.length === 0) throw new Error("a stack needs at least one part");
  const repeated = parts.find((p, i) => parts.findIndex((o) => o.name === p.name) !== i);
  if (repeated !== undefined)
    throw new Error(`part names must be distinct: "${repeated.name}" repeats`);
  const bad = parts.find((p) => !(p.value > 0));
  if (bad !== undefined) {
    throw new Error(`part "${bad.name}": a segment's value must be more than zero`);
  }
  const shared = parts.filter((p) => p.share !== undefined).length;
  if (shared !== 0 && shared !== parts.length) {
    throw new Error("every part carries a share, or none does");
  }
  if (table.rows.map((r) => r.label).join("\u0000") !== parts.map((p) => p.name).join("\u0000")) {
    throw new Error("the table must have one row per part, labelled with the part, in order");
  }
  const columns = shared === 0 ? 1 : 2;
  if (table.head.length !== columns + 1) {
    throw new Error(`the table must have ${String(columns)} columns after the label`);
  }
  parts.forEach((p, i) => {
    const cells = table.rows[i]?.cells ?? [];
    if (cells.length !== columns || cells[0] !== p.text || (shared > 0 && cells[1] !== p.share)) {
      throw new Error(`part "${p.name}": the table's cells must be the part's text and share`);
    }
  });
}

/** A rectangle with its right end rounded: the end segment of the stack. */
function endRounded(x: number, y: number, w: number, h: number, r: number): string {
  const k = Math.min(r, w, h / 2);
  const f = String;
  return `M${f(x)},${f(y)}H${f(x + w - k)}Q${f(x + w)},${f(y)} ${f(x + w)},${f(y + k)}V${f(y + h - k)}Q${f(x + w)},${f(y + h)} ${f(x + w - k)},${f(y + h)}H${f(x)}Z`;
}

function Segment({
  shape,
  style,
  name,
  last,
}: {
  shape: BarShapeProps;
  style: SeriesStyle;
  name: string;
  last: boolean;
}) {
  const { x, y, width, height } = shape;
  const drawn = last ? width : Math.max(width - SEGMENT_GAP, 0);
  return (
    <path
      data-segment=""
      data-part={name}
      data-width={width}
      data-end={last ? "" : undefined}
      fill={style.color}
      d={
        last
          ? endRounded(x, y, drawn, height, RADIUS)
          : `M${String(x)},${String(y)}h${String(drawn)}v${String(height)}h${String(-drawn)}Z`
      }
    />
  );
}

/** The readout: every part's name, amount and share, as delivered. */
function StackTooltip({ active, parts }: TooltipContentProps & { parts: StackPart[] }) {
  if (!active) return null;
  return (
    <div className="rounded-ds-sm bg-surface-inverse px-3 py-2 text-small text-text-on-action shadow-2">
      <ul>
        {parts.map((p) => (
          <ReadoutRow
            key={p.name}
            name={p.name}
            values={p.share === undefined ? [p.text] : [p.text, p.share]}
          />
        ))}
      </ul>
    </div>
  );
}

/** Rank order down the rows; the amount in medium weight, the share in the tertiary text colour. */
function RankedLegend({ parts, styles }: { parts: StackPart[]; styles: Map<string, SeriesStyle> }) {
  const share = parts.some((p) => p.share !== undefined);
  return (
    <ol
      aria-label="Ranked legend"
      className={`grid items-center gap-x-4 gap-y-2 text-small ${share ? "grid-cols-[auto_1fr_auto_auto]" : "grid-cols-[auto_1fr_auto]"}`}
    >
      {parts.map((p) => (
        <li key={p.name} className="col-span-full grid grid-cols-subgrid items-center">
          <svg width="12" height="12" aria-hidden="true">
            <rect width="12" height="12" rx="2" fill={styles.get(p.name)?.color} />
          </svg>
          <span className="text-text-primary">{p.name}</span>
          <b className="text-right font-medium tabular-nums text-text-primary">{p.text}</b>
          {p.share === undefined ? null : (
            <b className="text-right font-medium tabular-nums text-text-tertiary">{p.share}</b>
          )}
        </li>
      ))}
    </ol>
  );
}

function Chart({ title, parts }: Pick<StackChartProps, "title" | "parts">) {
  const styles = assignSeries(parts.map((p) => p.name));
  const row = { row: title, ...Object.fromEntries(parts.map((p, i) => [keyOf(i), p.value])) };
  return (
    <div className="flex flex-col gap-6 [&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-solid [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus">
      <ResponsiveContainer width="100%" height={ROW_HEIGHT}>
        <BarChart
          title={title}
          layout="vertical"
          data={[row]}
          margin={{ top: 4, right: 0, bottom: 4, left: 0 }}
        >
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis type="category" dataKey="row" hide />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={(props) => <StackTooltip {...props} parts={parts} />}
          />
          {parts.map((p, i) => {
            const style = styles.get(p.name);
            if (style === undefined) throw new Error(`no style for part "${p.name}"`);
            return (
              <Bar
                key={p.name}
                dataKey={keyOf(i)}
                name={p.name}
                stackId="debt"
                fill={style.color}
                barSize={BAR}
                isAnimationActive={false}
                shape={(shape: BarShapeProps) => (
                  <Segment
                    shape={shape}
                    style={style}
                    name={p.name}
                    last={i === parts.length - 1}
                  />
                )}
              />
            );
          })}
        </BarChart>
      </ResponsiveContainer>
      <RankedLegend parts={parts} styles={styles} />
    </div>
  );
}

/** One bar split into ranked parts, such as debt by instrument. */
export function StackChart({ title, as, note, subtitle, actions, parts, table }: StackChartProps) {
  check({ parts, table });
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <Chart title={title} parts={parts} />
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
