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
import { topRounded } from "./ColumnsChart";
import { useWrappedAxis, WrappedTick } from "./PathChart";
import { BASELINE, HEIGHT, YAxisLabels, type YTick } from "./TrendChart";

type Kind = "total" | "up" | "down";
type PresentStep = { label: string; kind: Kind; from: number; to: number; text: string };

export type WaterfallStep = PresentStep | { label: string; kind: "missing" };

interface WaterfallChartProps {
  title: string;
  as?: "h3" | "h4";
  note?: string;
  subtitle?: string;
  actions?: ReactNode;
  /**
   * `from` and `to` are the positions the module wrote, on the axis; `text` is the exact signed
   * label. Nothing is derived from another step.
   */
  steps: WaterfallStep[];
  yTicks: YTick[];
  /** The legend words; they are drawn in the order of the keys given. */
  legend: { total: string; down: string; up: string };
  /** One row per step, in order. The columns may be cases, so cells are not compared to steps. */
  table: { head: string[]; rows: TableRowData[]; endHeading?: string };
}

// Tokens for the three waterfall colours come later; one named constant each until then.
const TOTAL_COLOR = "var(--color-chart-1)";
const UP_COLOR = "var(--color-brand-400)";
const DOWN_COLOR = "var(--color-chart-3)";
const COLORS: Record<Kind, string> = { total: TOTAL_COLOR, up: UP_COLOR, down: DOWN_COLOR };

const LABEL_FILL = "var(--color-text-primary)";
const NA_FILL = "var(--color-text-tertiary)";
const MAX_BAR = 32;
const HAIRLINE = 1;
const LABEL_GAP = 4;
const RANGE = "range";

function check({ steps, table }: Pick<WaterfallChartProps, "steps" | "table">) {
  if (steps.length === 0) throw new Error("a waterfall needs at least one step");
  const repeated = steps.find((s, i) => steps.findIndex((o) => o.label === s.label) !== i);
  if (repeated !== undefined) {
    throw new Error(`step labels must be distinct: "${repeated.label}" repeats`);
  }
  for (const s of steps) {
    if (s.kind === "missing") continue;
    if (!(s.from >= 0) || !(s.to >= 0)) {
      throw new Error(
        `step "${s.label}": positions sit on one zero baseline, so they must be zero or more`,
      );
    }
    if (s.kind === "total" && s.from !== 0) {
      throw new Error(`step "${s.label}": a total starts at the baseline (from 0)`);
    }
    if (s.kind === "up" && s.to < s.from) {
      throw new Error(`step "${s.label}": an up step must not fall (to is below from)`);
    }
    if (s.kind === "down" && s.to > s.from) {
      throw new Error(`step "${s.label}": a down step must not rise (to is above from)`);
    }
  }
  if (table.rows.length !== steps.length) {
    throw new Error(`the table must have one row per step (${String(steps.length)} steps)`);
  }
  const short = table.rows.find((r) => r.cells.length !== table.head.length - 1);
  if (short !== undefined) {
    throw new Error(
      `table row "${short.label}" must have ${String(table.head.length - 1)} cells, one per column after the label`,
    );
  }
}

/** One present step: a floating column (a hairline when it is zero) and its label above it. */
function StepMark({ shape, step }: { shape: BarShapeProps; step: PresentStep }) {
  const { x, width } = shape;
  const zero = shape.height === 0;
  const h = zero ? HAIRLINE : Math.abs(shape.height);
  const y = Math.min(shape.y, shape.y + shape.height);
  return (
    <g>
      <path
        data-bar=""
        data-kind={step.kind}
        data-zero={zero ? "" : undefined}
        data-step={step.label}
        data-y={y}
        data-height={h}
        data-width={width}
        d={topRounded(x, y, width, h, zero ? 0 : width >= 24 ? 6 : 4)}
        fill={COLORS[step.kind]}
      />
      <text
        data-label=""
        data-step={step.label}
        x={x + width / 2}
        y={y - LABEL_GAP}
        textAnchor="middle"
        fontSize={12}
        fill={LABEL_FILL}
      >
        {step.text}
      </text>
    </g>
  );
}

/** "n.a." at the baseline in the slot of every missing step; the band is the plot width over the steps. */
function MissingMarks({ steps }: { steps: WaterfallStep[] }) {
  const scale = useXAxisScale();
  const area = usePlotArea();
  if (scale === undefined || area === undefined) return null;
  // Recharts' first pass runs before the axes are measured and places no step; draw nothing then.
  // Once any step is placed, one still unplaced is a fault.
  if (steps.every((s) => typeof scale(s.label) !== "number")) return null;
  return (
    <g>
      {steps.flatMap((s) => {
        if (s.kind !== "missing") return [];
        const start = scale(s.label);
        if (typeof start !== "number") {
          throw new Error(`step "${s.label}": no slot for the missing step`);
        }
        return [
          <text
            key={s.label}
            data-missing=""
            data-step={s.label}
            x={start + area.width / steps.length / 2}
            y={area.y + area.height - LABEL_GAP}
            textAnchor="middle"
            fontSize={12}
            fill={NA_FILL}
          >
            n.a.
          </text>,
        ];
      })}
    </g>
  );
}

/** The readout for the active step: its label and the exact text, or n.a. */
function WaterfallTooltip({
  active,
  label,
  steps,
}: TooltipContentProps & { steps: WaterfallStep[] }) {
  const step = steps.find((s) => s.label === String(label));
  if (!active || step === undefined) return null;
  return (
    <div className="rounded-ds-sm bg-surface-inverse px-3 py-2 text-small text-text-on-action shadow-2">
      <ul>
        <li className="flex justify-between gap-4">
          <span>{step.label}</span>{" "}
          <span className="tabular-nums">{step.kind === "missing" ? "n.a." : step.text}</span>
        </li>
      </ul>
    </div>
  );
}

function isKind(key: string): key is Kind {
  return key === "total" || key === "up" || key === "down";
}

function KindLegend({ legend }: { legend: WaterfallChartProps["legend"] }) {
  return (
    <ul aria-label="Legend" className="flex flex-wrap gap-x-5 gap-y-2">
      {Object.keys(legend)
        .filter(isKind)
        .map((kind) => (
          <li
            key={kind}
            data-kind={kind}
            className="flex items-center gap-2 text-small text-text-secondary"
          >
            <svg width="12" height="12" aria-hidden="true">
              <rect width="12" height="12" rx="2" fill={COLORS[kind]} />
            </svg>
            {legend[kind]}
          </li>
        ))}
    </ul>
  );
}

function Chart({
  title,
  steps,
  yTicks,
  legend,
}: Pick<WaterfallChartProps, "title" | "steps" | "yTicks" | "legend">) {
  const data = steps.map((s) => ({
    label: s.label,
    [RANGE]: s.kind === "missing" ? null : [s.from, s.to],
  }));
  const axis = useWrappedAxis(
    steps.map((s) => s.label),
    yTicks,
  );
  return (
    <div className="flex flex-col gap-3 [&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-solid [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus">
      <ResponsiveContainer width="100%" height={HEIGHT} onResize={axis.onResize}>
        <BarChart
          title={title}
          data={data}
          margin={{ top: 24, right: 24, bottom: 0, left: 0 }}
          barCategoryGap="20%"
        >
          <CartesianGrid vertical={false} stroke="var(--color-border-hairline)" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={BASELINE}
            tick={WrappedTick}
            interval={0}
            height={axis.height}
            tickMargin={8}
          />
          <YAxisLabels yTicks={yTicks} />
          <Tooltip
            isAnimationActive={false}
            cursor={false}
            content={(props) => <WaterfallTooltip {...props} steps={steps} />}
          />
          <MissingMarks steps={steps} />
          <Bar
            dataKey={RANGE}
            barSize={MAX_BAR}
            isAnimationActive={false}
            shape={(shape: BarShapeProps) => {
              const step = steps[shape.originalDataIndex];
              if (step === undefined || step.kind === "missing") {
                throw new Error(`no present step for bar ${String(shape.originalDataIndex)}`);
              }
              return <StepMark shape={shape} step={step} />;
            }}
          />
        </BarChart>
      </ResponsiveContainer>
      <KindLegend legend={legend} />
    </div>
  );
}

/** A walk between totals: each step floats from where the module wrote it to start to where it ends. */
export function WaterfallChart({
  title,
  as,
  note,
  subtitle,
  actions,
  steps,
  yTicks,
  legend,
  table,
}: WaterfallChartProps) {
  check({ steps, table });
  return (
    <ChartFrame title={title} as={as} note={note} subtitle={subtitle} actions={actions}>
      {(view) =>
        view === "chart" ? (
          <Chart title={title} steps={steps} yTicks={yTicks} legend={legend} />
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
