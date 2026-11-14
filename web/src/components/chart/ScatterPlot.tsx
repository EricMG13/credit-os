import type { ReactNode } from "react";
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import { ChartFrame } from "./ChartFrame";
import { ChartTable, type TableRowData } from "./ChartTable";
import { Mark } from "./marks";
import { assignSeries, type SeriesStyle } from "./series";
import { BASELINE, HEIGHT, TICK, type YTick } from "./TrendChart";

export interface ScatterPoint {
  name: string;
  /** Position only; null is missing. */
  x: number | null;
  y: number | null;
  /** The exact strings; null exactly where the measure is missing. */
  xText: string | null;
  yText: string | null;
  /** The issuer: drawn larger, in the first series style and labelled. At most one. */
  emphasis?: boolean;
}

interface ScatterAxis {
  title: string;
  /** The measure's name inside a sentence ("net leverage"), as the not-plotted note uses it. */
  short: string;
  ticks: YTick[];
}

interface ScatterPlotProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  x: ScatterAxis;
  y: ScatterAxis;
  /** The legend's name for the points that are not emphasised. */
  othersName: string;
  /** The issuer first, as delivered. */
  points: ScatterPoint[];
  /** One row per point, in order, with its x then its y string. */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

const LABEL = { fontSize: 12, fill: "var(--color-text-secondary)" };

function checkPair(p: ScatterPoint, which: "x" | "y", axis: ScatterAxis) {
  const value = p[which];
  const text = p[which === "x" ? "xText" : "yText"];
  if (value === null) {
    if (text !== null) throw new Error(`point "${p.name}": a missing ${which} takes no text`);
    return;
  }
  if (text === null) throw new Error(`point "${p.name}": a present ${which} needs a text`);
  const first = axis.ticks[0]?.value ?? 0;
  const last = axis.ticks[axis.ticks.length - 1]?.value ?? 0;
  if (!(value >= first && value <= last)) {
    throw new Error(`point "${p.name}": its ${which} is outside the ${which} axis`);
  }
}

function check({ x, y, points, table }: Pick<ScatterPlotProps, "x" | "y" | "points" | "table">) {
  if (points.length === 0) throw new Error("a scatter needs at least one point");
  for (const axis of [x, y]) {
    const v = axis.ticks.map((t) => t.value);
    if (v.length < 2 || v.some((t, i) => i > 0 && t <= (v[i - 1] ?? t))) {
      throw new Error(`axis "${axis.title}": ticks must be at least two, rising`);
    }
  }
  const repeated = points.find((p, i) => points.findIndex((o) => o.name === p.name) !== i);
  if (repeated !== undefined) {
    throw new Error(`point names must be distinct: "${repeated.name}" repeats`);
  }
  if (points.filter((p) => p.emphasis === true).length > 1) {
    throw new Error("at most one emphasised point");
  }
  for (const p of points) {
    checkPair(p, "x", x);
    checkPair(p, "y", y);
  }
  if (table.head.length !== 3) throw new Error("the table must have an x and a y column");
  if (table.rows.map((r) => r.label).join("\u0000") !== points.map((p) => p.name).join("\u0000")) {
    throw new Error("the table must have one row per point, labelled with the point, in order");
  }
  points.forEach((p, i) => {
    const cells = table.rows[i]?.cells ?? [];
    if (cells.length !== 2 || cells[0] !== p.xText || cells[1] !== p.yText) {
      throw new Error(`point "${p.name}": the table's cells must be the point's texts`);
    }
  });
}

interface Plotted {
  point: ScatterPoint;
  x: number;
  y: number;
}

function plotted(points: ScatterPoint[]): Plotted[] {
  return points.flatMap((point) =>
    point.x === null || point.y === null ? [] : [{ point, x: point.x, y: point.y }],
  );
}

/** The readout: the point's name and its exact strings. */
function ScatterTooltip({
  active,
  payload,
  x,
  y,
}: TooltipContentProps & Pick<ScatterPlotProps, "x" | "y">) {
  const row = (payload[0]?.payload ?? undefined) as Plotted | undefined;
  if (!active || row === undefined) return null;
  const { point } = row;
  return (
    <div className="rounded-ds-sm bg-surface-inverse px-3 py-2 text-small text-text-on-action shadow-2">
      <p className="font-semibold">{point.name}</p>
      <ul>
        <li className="flex justify-between gap-4">
          <span>{x.title}</span> <span className="tabular-nums">{point.xText}</span>
        </li>
        <li className="flex justify-between gap-4">
          <span>{y.title}</span> <span className="tabular-nums">{point.yText}</span>
        </li>
      </ul>
    </div>
  );
}

function Axes({ x, y }: Pick<ScatterPlotProps, "x" | "y">) {
  const axis = (a: ScatterAxis) => ({
    type: "number" as const,
    domain: [a.ticks[0]?.value ?? 0, a.ticks[a.ticks.length - 1]?.value ?? 0] as [number, number],
    ticks: a.ticks.map((t) => t.value),
    interval: 0 as const,
    tickFormatter: (v: number) => a.ticks.find((t) => t.value === v)?.label ?? "",
    tickLine: false,
    tick: TICK,
    tickMargin: 8,
  });
  return (
    <>
      <XAxis
        {...axis(x)}
        dataKey="x"
        axisLine={BASELINE}
        label={{ value: x.title, position: "insideBottom", offset: 8, ...LABEL }}
        height={48}
      />
      <YAxis
        {...axis(y)}
        dataKey="y"
        axisLine={false}
        width={64}
        label={{ value: y.title, angle: -90, position: "insideLeft", offset: 4, ...LABEL }}
      />
    </>
  );
}

/** The keys are the marker alone, as the points draw it: the issuer's circle, then the others'. */
function ScatterLegend({ names, styles }: { names: string[]; styles: Map<string, SeriesStyle> }) {
  return (
    <ul aria-label="Legend" className="flex flex-wrap justify-center gap-x-5 gap-y-2">
      {names.map((name, i) => {
        const style = styles.get(name);
        if (style === undefined) throw new Error(`no style for "${name}"`);
        return (
          <li key={name} className="flex items-center gap-2 text-small text-text-secondary">
            <svg width="12" height="12" aria-hidden="true">
              {i === 0 ? (
                <circle cx={6} cy={6} r={6} fill={style.color} />
              ) : (
                <Mark marker={style.marker} color={style.color} x={6} y={6} series={name} />
              )}
            </svg>
            {name}
          </li>
        );
      })}
    </ul>
  );
}

function Chart({
  title,
  x,
  y,
  othersName,
  points,
}: Pick<ScatterPlotProps, "title" | "x" | "y" | "othersName" | "points">) {
  const issuer = points.find((p) => p.emphasis === true);
  const names = issuer === undefined ? [othersName] : [issuer.name, othersName];
  const styles = assignSeries(names);
  const rows = plotted(points);
  const missing = points.filter((p) => p.x === null || p.y === null);
  return (
    <div className="flex flex-col gap-3 [&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-solid [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus">
      <ResponsiveContainer width="100%" height={HEIGHT + 24}>
        <ScatterChart title={title} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--color-border-hairline)" />
          <Axes x={x} y={y} />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={(props) => <ScatterTooltip {...props} x={x} y={y} />}
          />
          <Scatter
            data={rows}
            isAnimationActive={false}
            shape={(props: { cx?: number; cy?: number; payload?: Plotted }) => {
              const { cx, cy, payload } = props;
              if (payload === undefined)
                throw new Error("a scatter mark arrived without its point");
              // Recharts' first pass runs before the axes are measured and gives no position;
              // nothing is drawn then, and the measured pass draws the mark.
              if (typeof cx !== "number" || typeof cy !== "number") return <g />;
              const name = payload.point.emphasis === true ? names[0] : othersName;
              const style = styles.get(name ?? othersName);
              if (style === undefined) throw new Error(`no style for "${String(name)}"`);
              return (
                <g data-point={payload.point.name}>
                  {payload.point.emphasis === true ? (
                    <>
                      <circle cx={cx} cy={cy} r={7} fill={style.color} />
                      <text
                        x={cx - 12}
                        y={cy + 14}
                        textAnchor="end"
                        fontSize={12}
                        fontWeight={500}
                        fill="var(--color-text-primary)"
                      >
                        {payload.point.name}
                      </text>
                    </>
                  ) : (
                    <Mark
                      marker={style.marker}
                      color={style.color}
                      x={cx}
                      y={cy}
                      series={othersName}
                    />
                  )}
                </g>
              );
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
      {names.length >= 2 ? <ScatterLegend names={names} styles={styles} /> : null}
      {missing.length === 0 ? null : (
        <p className="text-xs font-medium text-text-tertiary">
          Not plotted:{" "}
          {missing
            .map((p) => {
              const gaps = [p.x === null ? x.short : null, p.y === null ? y.short : null].filter(
                (s) => s !== null,
              );
              return `${p.name} (${gaps.join(" and ")} n.a.)`;
            })
            .join(", ")}
          .
        </p>
      )}
    </div>
  );
}

/** Two measures against each other, one mark per issuer; the issuer stands out. */
export function ScatterPlot({
  title,
  as,
  note,
  subtitle,
  actions,
  x,
  y,
  othersName,
  points,
  table,
}: ScatterPlotProps) {
  check({ x, y, points, table });
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <Chart title={title} x={x} y={y} othersName={othersName} points={points} />
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
