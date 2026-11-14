import { Fragment, type ReactNode } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  usePlotArea,
  useXAxisScale,
  XAxis,
  type TooltipContentProps,
} from "recharts";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableCell, type TableRowData } from "./ChartTable";
import { Mark } from "./marks";
import { assignSeries } from "./series";
import { BASELINE, HEIGHT, Legend, TICK, YAxisLabels, type YTick } from "./TrendChart";

interface PathSeries {
  name: string;
  values: (number | null)[];
  /** The exact text drawn at each point; null draws none. */
  labels: (string | null)[];
}

interface PathChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /** Oldest first: the x-axis. */
  periods: string[];
  series: PathSeries[];
  /**
   * A dashed vertical line with its label: "on" draws it at the period's point, "after" at the
   * boundary between that period and the next.
   */
  divider?: { period: string; at: "on" | "after"; label: string };
  yTicks: YTick[];
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

const LABEL_GAP = 10;
const TEXT_FILL = "var(--color-text-secondary)";
const LABEL_FILL = "var(--color-text-primary)";
const NA_FILL = "var(--color-text-tertiary)";

function keyOf(i: number): string {
  return `s${String(i)}`;
}

function check({
  periods,
  series,
  divider,
  table,
}: Pick<PathChartProps, "periods" | "series" | "divider" | "table">) {
  const repeated = series.find((s, i) => series.findIndex((o) => o.name === s.name) !== i);
  if (repeated !== undefined)
    throw new Error(`series names must be distinct: "${repeated.name}" repeats`);
  const columns = table.head.slice(1);
  if (columns.length !== periods.length || columns.some((c, i) => c !== periods[i])) {
    throw new Error("the table's columns must be the periods, in the same order");
  }
  const n = periods.length;
  const bad = series.find((s) => s.values.length !== n || s.labels.length !== n);
  if (bad !== undefined) {
    throw new Error(
      `series "${bad.name}" must have one value and one label per period (${String(n)} periods)`,
    );
  }
  if (divider !== undefined) {
    const at = periods.indexOf(divider.period);
    if (at < 0) throw new Error(`divider period "${divider.period}" is not one of the periods`);
    if (divider.at === "after" && at === periods.length - 1) {
      throw new Error(
        `divider "after" ${divider.period} needs a next period; it is the last period`,
      );
    }
  }
}

export function cellText(cell: TableCell | undefined): string {
  if (cell === undefined) throw new Error("the table has no cell for this period");
  if (cell === null) return "n.a.";
  if (typeof cell === "string") return cell;
  return "withheld" in cell ? "Withheld" : "Not established for this run";
}

/** One readout line: a name, then its exact strings, each in tabular figures. */
export function ReadoutRow({ name, values }: { name: string; values: string[] }) {
  return (
    <li className="flex justify-between gap-4">
      <span>{name}</span>
      {values.map((v, i) => (
        <Fragment key={i}>
          {" "}
          <span className="tabular-nums">{v}</span>
        </Fragment>
      ))}
    </li>
  );
}

/** The readout for the active period: the table's exact strings, nothing computed. */
function PathTooltip({
  active,
  label,
  periods,
  rows,
}: TooltipContentProps & { periods: string[]; rows: TableRowData[] }) {
  const index = periods.indexOf(String(label));
  if (!active || index < 0) return null;
  return (
    <div className="rounded-ds-sm bg-surface-inverse px-3 py-2 text-small text-text-on-action shadow-2">
      <p className="font-semibold">{label}</p>
      <ul>
        {rows.map((row, i) => (
          <ReadoutRow key={i} name={row.label} values={[cellText(row.cells[index])]} />
        ))}
      </ul>
    </div>
  );
}

/**
 * The dashed divider, placed from the x scale so it can sit on a point or on a boundary.
 * Recharts' first pass runs before the axes are measured and gives the scale no position for a
 * period name; nothing is drawn for that pass, and the measured pass draws the line.
 */
function Divider({
  divider,
  next,
}: {
  divider: NonNullable<PathChartProps["divider"]>;
  next: string | undefined;
}) {
  const scale = useXAxisScale();
  const area = usePlotArea();
  if (scale === undefined || area === undefined) return null;
  const here = scale(divider.period);
  const there = next === undefined ? undefined : scale(next);
  if (typeof here !== "number") return null;
  if (divider.at === "after" && typeof there !== "number") return null;
  const x = divider.at === "on" || typeof there !== "number" ? here : (here + there) / 2;
  return (
    <g>
      <line
        data-divider=""
        x1={x}
        x2={x}
        y1={area.y}
        y2={area.y + area.height}
        stroke="var(--color-border-control)"
        strokeDasharray="4 4"
      />
      <text x={x} y={area.y - 8} textAnchor="middle" fontSize={12} fill={TEXT_FILL}>
        {divider.label}
      </text>
    </g>
  );
}

function Chart({
  title,
  periods,
  series,
  divider,
  yTicks,
  rows,
}: Pick<PathChartProps, "title" | "periods" | "series" | "divider" | "yTicks"> & {
  rows: TableRowData[];
}) {
  const styles = assignSeries(series.map((s) => s.name));
  const data = periods.map((period, index) => ({
    period,
    index,
    ...Object.fromEntries(series.map((s, i) => [keyOf(i), s.values[index] ?? null])),
  }));
  const allMissing = periods.filter((_, p) => series.every((s) => s.values[p] === null));
  return (
    <div className="flex flex-col gap-3 [&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-solid [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus">
      <ResponsiveContainer width="100%" height={HEIGHT}>
        <LineChart title={title} data={data} margin={{ top: 24, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-border-hairline)" />
          <XAxis dataKey="period" tickLine={false} axisLine={BASELINE} tick={TICK} tickMargin={8} />
          <YAxisLabels yTicks={yTicks} />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={(props) => <PathTooltip {...props} periods={periods} rows={rows} />}
          />
          {divider === undefined ? null : (
            <Divider divider={divider} next={periods[periods.indexOf(divider.period) + 1]} />
          )}
          {allMissing.map((period) => (
            <ReferenceLine
              key={period}
              x={period}
              stroke="none"
              label={{ value: "n.a.", position: "insideBottom", fill: NA_FILL, fontSize: 12 }}
            />
          ))}
          {series.map((s, i) => {
            const style = styles.get(s.name);
            if (style === undefined) throw new Error(`no style for series "${s.name}"`);
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
                dot={({ cx, cy, value, index }) => {
                  if (
                    typeof cx !== "number" ||
                    typeof cy !== "number" ||
                    typeof value !== "number"
                  ) {
                    return null;
                  }
                  const label = s.labels[index];
                  return (
                    <g key={index}>
                      <Mark
                        marker={style.marker}
                        color={style.color}
                        x={cx}
                        y={cy}
                        series={s.name}
                      />
                      {label === null || label === undefined ? null : (
                        <text
                          data-label=""
                          data-series={s.name}
                          x={cx}
                          y={i === 0 ? cy - LABEL_GAP : cy + LABEL_GAP + 8}
                          textAnchor="middle"
                          fontSize={12}
                          fill={LABEL_FILL}
                        >
                          {label}
                        </text>
                      )}
                    </g>
                  );
                }}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
      {series.length >= 2 ? <Legend names={series.map((s) => s.name)} styles={styles} /> : null}
    </div>
  );
}

/** Lines over periods, several series, one period marked, chosen points labelled directly. */
export function PathChart({
  title,
  as,
  note,
  subtitle,
  actions,
  periods,
  series,
  divider,
  yTicks,
  table,
}: PathChartProps) {
  check({ periods, series, divider, table });
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <Chart
            title={title}
            periods={periods}
            series={series}
            divider={divider}
            yTicks={yTicks}
            rows={table.rows}
          />
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
