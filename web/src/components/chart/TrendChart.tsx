import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import { Missing } from "@/components/gap/Missing";
import { ChartFrame } from "./ChartFrame";
import { Mark } from "./marks";
import { assignSeries, SERIES, type SeriesStyle } from "./series";

interface SeriesData {
  name: string;
  values: (number | null)[];
}

interface TableRow {
  name: string;
  /** The figure as the caller formats it; null is a missing value. */
  cells: (string | null)[];
}

interface TrendChartProps {
  title: string;
  note?: string;
  /** Oldest first: the x-axis. */
  periods: string[];
  series: SeriesData[];
  /** The same data as display strings, one row per series. */
  table: TableRow[];
  /** The y-axis ticks and their labels, supplied by the caller. Without them the axis has no labels. */
  yTicks?: YTick[];
}

interface YTick {
  value: number;
  label: string;
}

const HEIGHT = 240;
const TICK = { fontSize: 12, fill: "var(--color-text-tertiary)" };
const BASELINE = { stroke: "var(--color-border-control)", strokeWidth: 1 };

function keyOf(i: number): string {
  return `s${String(i)}`;
}

/** The styles in legend order: each of the first six names, then a single Other. */
function legendEntries(names: string[], styles: Map<string, SeriesStyle>) {
  const other = SERIES[SERIES.length - 1];
  const entries = names.slice(0, SERIES.length - 1).map((name) => ({
    name,
    style: styles.get(name),
  }));
  return names.length > SERIES.length - 1 ? [...entries, { name: "Other", style: other }] : entries;
}

function Legend({ names, styles }: { names: string[]; styles: Map<string, SeriesStyle> }) {
  return (
    <ul aria-label="Legend" className="flex flex-wrap gap-x-5 gap-y-2">
      {legendEntries(names, styles).map(({ name, style }) => (
        <li key={name} className="flex items-center gap-2 text-small text-text-secondary">
          {style === undefined ? null : (
            <svg width="28" height="12" aria-hidden="true">
              <line
                x1="0"
                x2="28"
                y1="6"
                y2="6"
                stroke={style.color}
                strokeWidth="2"
                strokeDasharray={style.dash}
              />
              <Mark marker={style.marker} color={style.color} x={14} y={6} series={name} />
            </svg>
          )}
          {name}
        </li>
      ))}
    </ul>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  table,
}: TooltipContentProps & { table: TableRow[] }) {
  const index = (payload[0]?.payload as { index?: number } | undefined)?.index;
  if (!active || index === undefined) return null;
  return (
    <div className="rounded-ds-sm bg-surface-inverse px-3 py-2 text-small text-text-on-action shadow-2">
      <p className="font-semibold">{label}</p>
      <ul>
        {table.map((row) => (
          <li key={row.name} className="flex justify-between gap-4">
            <span>{row.name}</span>
            <span className="tabular-nums">{row.cells[index] ?? "n.a."}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function YAxisLabels({ yTicks }: { yTicks: YTick[] | undefined }) {
  if (yTicks === undefined || yTicks.length === 0) {
    return <YAxis width={0} tick={false} tickLine={false} axisLine={false} />;
  }
  const first = yTicks[0]?.value ?? 0;
  const last = yTicks[yTicks.length - 1]?.value ?? 0;
  const labels = new Map(yTicks.map((t) => [t.value, t.label]));
  return (
    <YAxis
      width="auto"
      tickLine={false}
      axisLine={false}
      tick={TICK}
      tickMargin={8}
      domain={[first, last]}
      ticks={yTicks.map((t) => t.value)}
      interval={0}
      tickFormatter={(v: number) => labels.get(v) ?? ""}
    />
  );
}

function check({ periods, series, table }: Pick<TrendChartProps, "periods" | "series" | "table">) {
  const same = series.length === table.length && series.every((s, i) => s.name === table[i]?.name);
  if (!same) throw new Error("series and table must carry the same names in the same order");
  const n = periods.length;
  const bad = series.find((s, i) => s.values.length !== n || table[i]?.cells.length !== n);
  if (bad !== undefined) {
    throw new Error(
      `series "${bad.name}" must have one value and one cell per period (${String(n)} periods)`,
    );
  }
}

function Chart({ periods, series, table, yTicks }: Omit<TrendChartProps, "title" | "note">) {
  const styles = assignSeries(series.map((s) => s.name));
  const data = periods.map((period, index) => ({
    period,
    index,
    ...Object.fromEntries(series.map((s, i) => [keyOf(i), s.values[index] ?? null])),
  }));
  return (
    <div className="flex flex-col gap-3">
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-border-hairline)" />
          <XAxis dataKey="period" tickLine={false} axisLine={BASELINE} tick={TICK} tickMargin={8} />
          <YAxisLabels yTicks={yTicks} />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={(props) => <ChartTooltip {...props} table={table} />}
          />
          {series.map((s, i) => {
            const style = styles.get(s.name);
            if (style === undefined) return null;
            return (
              <Line
                key={s.name}
                dataKey={keyOf(i)}
                name={s.name}
                stroke={style.color}
                strokeWidth={2}
                strokeDasharray={style.dash}
                connectNulls={false}
                isAnimationActive={false}
                activeDot={false}
                dot={({ cx, cy, value, index }) =>
                  typeof cx === "number" && typeof cy === "number" && typeof value === "number" ? (
                    <Mark
                      key={index}
                      marker={style.marker}
                      color={style.color}
                      x={cx}
                      y={cy}
                      series={s.name}
                    />
                  ) : null
                }
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
      {series.length >= 2 ? <Legend names={series.map((s) => s.name)} styles={styles} /> : null}
    </div>
  );
}

function DataTable({
  title,
  periods,
  table,
}: Pick<TrendChartProps, "title" | "periods" | "table">) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-small">
        <caption className="sr-only">{title}</caption>
        <thead>
          <tr className="border-b border-border-hairline">
            <td />
            {periods.map((p) => (
              <th key={p} scope="col" className="px-3 py-2 text-right font-semibold">
                {p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.map((row) => (
            <tr key={row.name} className="border-b border-border-hairline">
              <th scope="row" className="px-3 py-2 text-left font-semibold">
                {row.name}
              </th>
              {periods.map((p, i) => (
                <td key={p} className="px-3 py-2 text-right tabular-nums">
                  {row.cells[i] ?? <Missing />}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A line chart over periods, with the Chart or Table toggle on the same data. */
export function TrendChart({ title, note, periods, series, table, yTicks }: TrendChartProps) {
  check({ periods, series, table });
  return (
    <ChartFrame title={title} note={note}>
      {(view) =>
        view === "chart" ? (
          <Chart periods={periods} series={series} table={table} yTicks={yTicks} />
        ) : (
          <DataTable title={title} periods={periods} table={table} />
        )
      }
    </ChartFrame>
  );
}
