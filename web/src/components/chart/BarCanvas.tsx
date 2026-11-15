import type { ReactNode } from "react";
import {
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  type TooltipContentProps,
} from "recharts";
import { useWrappedAxis, WrappedTick } from "./PathChart";
import { BASELINE, HEIGHT, YAxisLabels, type YTick } from "./TrendChart";

/** What recharts hands a tooltip's content function. */
export type BarTooltipProps = TooltipContentProps;

interface BarCanvasProps {
  title: string;
  /** The recharts data; each row carries `xKey`. */
  data: Record<string, unknown>[];
  /** The row key holding the category on the x-axis. */
  xKey: string;
  /** The x-axis categories, in order. */
  categories: string[];
  yTicks: YTick[];
  /** Left to recharts' own gap when not given. */
  barGap?: number;
  tooltip: (props: BarTooltipProps) => ReactNode;
  /** The legend, drawn under the plot; null for none. */
  legend: ReactNode;
  /** The marks, drawn after the grid, axes and tooltip. */
  children: ReactNode;
}

/** The bar plot shared by the column and waterfall charts: focus ring, grid, wrapped axis, tooltip. */
export function BarCanvas({
  title,
  data,
  xKey,
  categories,
  yTicks,
  barGap,
  tooltip,
  legend,
  children,
}: BarCanvasProps) {
  const axis = useWrappedAxis(categories, yTicks);
  return (
    <div className="flex flex-col gap-3 [&_.recharts-surface:focus-visible]:outline-2 [&_.recharts-surface:focus-visible]:outline-solid [&_.recharts-surface:focus-visible]:outline-offset-2 [&_.recharts-surface:focus-visible]:outline-focus">
      <ResponsiveContainer width="100%" height={HEIGHT} onResize={axis.onResize}>
        <BarChart
          title={title}
          data={data}
          margin={{ top: 24, right: 24, bottom: 0, left: 0 }}
          {...(barGap === undefined ? {} : { barGap })}
          barCategoryGap="20%"
        >
          <CartesianGrid vertical={false} stroke="var(--color-border-hairline)" />
          <XAxis
            dataKey={xKey}
            tickLine={false}
            axisLine={BASELINE}
            tick={WrappedTick}
            interval={0}
            height={axis.height}
            tickMargin={8}
          />
          <YAxisLabels yTicks={yTicks} />
          <Tooltip isAnimationActive={false} cursor={false} content={tooltip} />
          {children}
        </BarChart>
      </ResponsiveContainer>
      {legend}
    </div>
  );
}
