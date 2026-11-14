import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  usePlotArea,
  useXAxisScale,
  XAxis,
  type BarShapeProps,
  type TooltipContentProps,
} from "recharts";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";
import { cellText } from "./PathChart";
import { assignSeries, type SeriesStyle } from "./series";
import { BASELINE, HEIGHT, TICK, YAxisLabels, type YTick } from "./TrendChart";

interface ColumnsSeries {
  name: string;
  values: (number | null)[];
  /** The exact text drawn above each bar; required for a present value, null for a missing one. */
  labels: (string | null)[];
}

interface ColumnsChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** The x-axis categories, in order. */
  groups: string[];
  series: ColumnsSeries[];
  yTicks: YTick[];
  /** One row per group, one cell per series, in series order. */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

const LABEL_FILL = "var(--color-text-primary)";
const NA_FILL = "var(--color-text-tertiary)";
const MAX_BAR = 32;
/** Three or more series: narrower bars and wider gaps, so no label meets a neighbour. */
const NARROW_BAR = 12;
const NARROW_GAP = 12;
const WIDE_GAP = 2;
const ZERO_MARK = 2;
const LABEL_GAP = 4;
/** The mock's fix for three-series groups: the middle label one 16px line higher. */
const MIDDLE_RAISE = 16;

function keyOf(i: number): string {
  return `s${String(i)}`;
}

function check({ groups, series, table }: Pick<ColumnsChartProps, "groups" | "series" | "table">) {
  const repeated = series.find((s, i) => series.findIndex((o) => o.name === s.name) !== i);
  if (repeated !== undefined)
    throw new Error(`series names must be distinct: "${repeated.name}" repeats`);
  const n = groups.length;
  const bad = series.find((s) => s.values.length !== n || s.labels.length !== n);
  if (bad !== undefined) {
    throw new Error(
      `series "${bad.name}" must have one value and one label per group (${String(n)} groups)`,
    );
  }
  for (const s of series) {
    groups.forEach((group, g) => {
      const present = s.values[g] !== null;
      const labelled = s.labels[g] !== null;
      if (present && !labelled) {
        throw new Error(`series "${s.name}", group "${group}": a present value needs a label`);
      }
      if (!present && labelled) {
        throw new Error(`series "${s.name}", group "${group}": a missing value takes no label`);
      }
    });
  }
  const repeatedGroup = groups.find((g, i) => groups.indexOf(g) !== i);
  if (repeatedGroup !== undefined) {
    throw new Error(`group names must be distinct: "${repeatedGroup}" repeats`);
  }
  for (const s of series) {
    const negative = s.values.findIndex((v) => v !== null && !(v >= 0));
    if (negative >= 0) {
      throw new Error(
        `series "${s.name}", group "${groups[negative] ?? ""}": values sit on one zero baseline, so they must be zero or more`,
      );
    }
  }
  const names = series.map((s) => s.name);
  if (table.head.slice(1).join("\u0000") !== names.join("\u0000")) {
    throw new Error(`table columns after the first must be the series names, in order`);
  }
  if (table.rows.map((r) => r.label).join("\u0000") !== groups.join("\u0000")) {
    throw new Error(`the table must have one row per group, labelled with the group, in order`);
  }
  const short = table.rows.find((r) => r.cells.length !== series.length);
  if (short !== undefined) {
    throw new Error(
      `table row "${short.label}" must have one cell per series (${String(series.length)})`,
    );
  }
}

/** Top corners only, radius `r`; the path is the bar's rectangle. */
export function topRounded(x: number, y: number, w: number, h: number, r: number): string {
  const k = Math.min(r, w / 2, h);
  return `M${String(x)},${String(y + h)}V${String(y + k)}Q${String(x)},${String(y)} ${String(x + k)},${String(y)}H${String(x + w - k)}Q${String(x + w)},${String(y)} ${String(x + w)},${String(y + k)}V${String(y + h)}Z`;
}

/** One present value: a bar (a minimal mark when it is zero) and its label above it. */
function BarMark({
  shape,
  style,
  name,
  group,
  label,
  raise,
}: {
  shape: BarShapeProps;
  style: SeriesStyle;
  name: string;
  group: string;
  label: string;
  /** Pixels the label sits higher, so neighbouring labels in a crowded group do not meet. */
  raise: number;
}) {
  const area = usePlotArea();
  if (area === undefined) return null;
  const { x, width } = shape;
  const baseline = area.y + area.height;
  const zero = !(shape.height > 0);
  const h = zero ? ZERO_MARK : shape.height;
  const top = baseline - h;
  return (
    <g>
      <path
        data-bar=""
        data-zero={zero ? "" : undefined}
        data-series={name}
        data-group={group}
        x={x}
        width={width}
        height={h}
        d={topRounded(x, top, width, h, width >= 24 ? 6 : 4)}
        fill={style.color}
      />
      <text
        data-label=""
        data-series={name}
        x={x + width / 2}
        y={top - LABEL_GAP - raise}
        textAnchor="middle"
        fontSize={12}
        fill={LABEL_FILL}
      >
        {label}
      </text>
    </g>
  );
}

/**
 * "n.a." at the baseline in the slot of every missing value. Recharts draws no bar for a null, so
 * the slot is found from the group's band (the plot's width over the groups): the series' bars sit centred in it, side by side.
 */
function MissingMarks({
  groups,
  series,
  barSize,
  barGap,
}: {
  groups: string[];
  series: ColumnsSeries[];
  barSize: number;
  barGap: number;
}) {
  const scale = useXAxisScale();
  const area = usePlotArea();
  if (scale === undefined || area === undefined) return null;
  // Recharts' first pass runs before the axes are measured and the scale places no group; nothing
  // is drawn for that pass. Once any group is placed the axis is measured, and a group that is
  // still unplaced is a fault, not a pass to wait out.
  if (groups.every((group) => typeof scale(group) !== "number")) return null;
  const total = series.length * barSize + (series.length - 1) * barGap;
  return (
    <g>
      {series.flatMap((s, i) =>
        groups.flatMap((group, g) => {
          if (s.values[g] !== null) return [];
          const start = scale(group);
          if (typeof start !== "number") {
            throw new Error(`series "${s.name}", group "${group}": no slot for the missing value`);
          }
          const centre = start + area.width / groups.length / 2;
          return [
            <text
              key={`${s.name}/${group}`}
              data-missing=""
              data-series={s.name}
              data-group={group}
              x={centre - total / 2 + i * (barSize + barGap) + barSize / 2}
              y={area.y + area.height - LABEL_GAP}
              textAnchor="middle"
              fontSize={12}
              fill={NA_FILL}
            >
              n.a.
            </text>,
          ];
        }),
      )}
    </g>
  );
}

/** The readout for the active group: the table row's exact strings under the series names. */
function ColumnsTooltip({
  active,
  label,
  groups,
  head,
  rows,
}: TooltipContentProps & { groups: string[]; head: string[]; rows: TableRowData[] }) {
  const index = groups.indexOf(String(label));
  const row = rows[index];
  if (!active || row === undefined) return null;
  return (
    <div className="rounded-ds-sm bg-surface-inverse px-3 py-2 text-small text-text-on-action shadow-2">
      <p className="font-semibold">{label}</p>
      <ul>
        {row.cells.map((cell, i) => (
          <li key={i} className="flex justify-between gap-4">
            <span>{head[i + 1]}</span> <span className="tabular-nums">{cellText(cell)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Square swatches in bar order: a bar is a filled area, not a line. */
export function BarLegend({
  names,
  styles,
  centered = false,
}: {
  names: string[];
  styles: Map<string, SeriesStyle>;
  /** The mock's `.lg.h`: the entries centred under the chart. */
  centered?: boolean;
}) {
  return (
    <ul
      aria-label="Legend"
      className={`flex flex-wrap gap-x-5 gap-y-2 ${centered ? "justify-center" : ""}`}
    >
      {names.map((name) => (
        <li key={name} className="flex items-center gap-2 text-small text-text-secondary">
          <svg width="12" height="12" aria-hidden="true">
            <rect width="12" height="12" rx="2" fill={styles.get(name)?.color} />
          </svg>
          {name}
        </li>
      ))}
    </ul>
  );
}

function Chart({
  title,
  groups,
  series,
  yTicks,
  table,
}: Pick<ColumnsChartProps, "title" | "groups" | "series" | "yTicks" | "table">) {
  const styles = assignSeries(series.map((s) => s.name));
  const narrow = series.length >= 3;
  const barSize = narrow ? NARROW_BAR : MAX_BAR;
  const barGap = narrow ? NARROW_GAP : WIDE_GAP;
  const data = groups.map((group, index) => ({
    group,
    ...Object.fromEntries(series.map((s, i) => [keyOf(i), s.values[index] ?? null])),
  }));
  return (
    <div className="flex flex-col gap-3 [&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-solid [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus">
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <BarChart
          title={title}
          data={data}
          margin={{ top: 24, right: 24, bottom: 0, left: 0 }}
          barGap={barGap}
          barCategoryGap="20%"
        >
          <CartesianGrid vertical={false} stroke="var(--color-border-hairline)" />
          <XAxis dataKey="group" tickLine={false} axisLine={BASELINE} tick={TICK} tickMargin={8} />
          <YAxisLabels yTicks={yTicks} />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={(props) => (
              <ColumnsTooltip {...props} groups={groups} head={table.head} rows={table.rows} />
            )}
          />
          <MissingMarks groups={groups} series={series} barSize={barSize} barGap={barGap} />
          {series.map((s, i) => {
            const style = styles.get(s.name);
            if (style === undefined) throw new Error(`no style for series "${s.name}"`);
            return (
              <Bar
                key={s.name}
                dataKey={keyOf(i)}
                name={s.name}
                fill={style.color}
                barSize={barSize}
                isAnimationActive={false}
                shape={(shape: BarShapeProps) => {
                  const at = shape.originalDataIndex;
                  const group = groups[at];
                  const label = s.labels[at];
                  if (group === undefined || label === null || label === undefined) {
                    throw new Error(`series "${s.name}": no group or label for bar ${String(at)}`);
                  }
                  return (
                    <BarMark
                      shape={shape}
                      style={style}
                      name={s.name}
                      group={group}
                      label={label}
                      raise={narrow && i === 1 ? MIDDLE_RAISE : 0}
                    />
                  );
                }}
              />
            );
          })}
        </BarChart>
      </ResponsiveContainer>
      {series.length >= 2 ? <BarLegend names={series.map((s) => s.name)} styles={styles} /> : null}
    </div>
  );
}

/** Amounts side by side on one zero baseline: maturities by year, recovery by class and case. */
export function ColumnsChart({
  title,
  as,
  note,
  subtitle,
  actions,
  groups,
  series,
  yTicks,
  table,
}: ColumnsChartProps) {
  check({ groups, series, table });
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <Chart title={title} groups={groups} series={series} yTicks={yTicks} table={table} />
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
