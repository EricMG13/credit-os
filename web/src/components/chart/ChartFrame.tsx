import { useId, useState, type ReactNode } from "react";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";

export type ChartView = "chart" | "table";

interface ChartFrameProps {
  title: string;
  /** The heading level: the one that follows the heading of the section the chart sits in. */
  as?: "h3" | "h4";
  /** The basis of the figures, in small text under the chart. */
  note?: string;
  /** A line under the title, saying what the chart shows; the figure is described by it. */
  subtitle?: string;
  /** Drawn in the header row before the Chart or Table toggle, for example a trace control. */
  actions?: ReactNode;
  /** Draws the chart or the table form of the same data. */
  children: (view: ChartView) => ReactNode;
}

/** A titled frame with the Chart or Table toggle. It owns which side is shown. */
export function ChartFrame({
  title,
  as: Heading = "h4",
  note,
  subtitle,
  actions,
  children,
}: ChartFrameProps) {
  const [view, setView] = useState<ChartView>("chart");
  const hasSubtitle = subtitle !== undefined && subtitle !== "";
  const titleId = useId();
  const subtitleId = useId();
  const heading = (
    <Heading id={titleId} className="min-w-48 flex-1 font-display text-h4 text-text-primary">
      {title}
    </Heading>
  );
  return (
    <figure
      aria-labelledby={titleId}
      aria-describedby={hasSubtitle ? subtitleId : undefined}
      className="flex flex-col gap-4"
    >
      <div className="flex flex-wrap items-center gap-3">
        {hasSubtitle ? (
          <div className="min-w-48 flex-1">
            {heading}
            <p id={subtitleId} className="text-small text-text-tertiary">
              {subtitle}
            </p>
          </div>
        ) : (
          heading
        )}
        <div className="ml-auto flex items-center gap-3">
          {actions}
          <ButtonGroup
            size="sm"
            aria-label={`${title}: Chart or Table`}
            disallowEmptySelection
            selectedKeys={[view]}
            onSelectionChange={(keys) => {
              setView(keys.has("table") ? "table" : "chart");
            }}
          >
            <ButtonGroupItem id="chart">Chart</ButtonGroupItem>
            <ButtonGroupItem id="table">Table</ButtonGroupItem>
          </ButtonGroup>
        </div>
      </div>
      {children(view)}
      {note === undefined ? null : (
        <figcaption className="text-small text-text-secondary">{note}</figcaption>
      )}
    </figure>
  );
}
