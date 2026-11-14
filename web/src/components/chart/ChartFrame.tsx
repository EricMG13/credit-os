import { useId, useState, type ReactNode } from "react";
import { ButtonGroup, ButtonGroupItem } from "@/components/base/button-group/button-group";

export type ChartView = "chart" | "table";

interface ChartFrameProps {
  title: string;
  /** The basis of the figures, in small text under the chart. */
  note?: string;
  /** Draws the chart or the table form of the same data. */
  children: (view: ChartView) => ReactNode;
}

/** A titled frame with the Chart or Table toggle. It owns which side is shown. */
export function ChartFrame({ title, note, children }: ChartFrameProps) {
  const [view, setView] = useState<ChartView>("chart");
  const titleId = useId();
  return (
    <figure aria-labelledby={titleId} className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 id={titleId} className="font-display text-h4 text-text-primary">
          {title}
        </h4>
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
      {children(view)}
      {note === undefined ? null : (
        <figcaption className="text-small text-text-secondary">{note}</figcaption>
      )}
    </figure>
  );
}
