import type { ReactNode } from "react";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { Card } from "@/components/card/Card";
import { Missing } from "@/components/gap/Missing";
import type { Figure, RunRecord } from "../slice-activity";

function Item({
  caption,
  value,
  children,
}: {
  caption: string;
  value: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <span className="text-xs font-medium text-text-tertiary">{caption}</span>
      <span className="font-display text-metric tabular-nums text-text-primary">{value}</span>
      {children}
    </div>
  );
}

function WithBar({ caption, figure }: { caption: string; figure: Figure }) {
  const { label, value, max } = figure.bar;
  return (
    <Item caption={caption} value={figure.value ?? <Missing />}>
      <ProgressBar value={value} max={max} label={label} />
    </Item>
  );
}

/** Spend, modules finished and elapsed time. Every string arrives in the slice; nothing counts. */
export function Summary({ run }: { run: RunRecord }) {
  return (
    <Card>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-8">
        <WithBar caption="Spend" figure={run.spend} />
        <WithBar caption="Modules finished" figure={run.finished} />
        <Item caption="Elapsed" value={run.elapsed.value ?? <Missing />}>
          <span className="text-sm text-text-tertiary">{run.elapsed.note}</span>
        </Item>
      </div>
    </Card>
  );
}
