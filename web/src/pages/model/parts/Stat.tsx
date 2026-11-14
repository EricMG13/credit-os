import type { ReactNode } from "react";
import { Missing } from "@/components/gap/Missing";

/**
 * One measure: its label with a trace control, the value, the delivered delta line and a sentence
 * on what it means. A missing value draws "n.a."; the delta is drawn as given, in neutral text.
 * Kit need: the kit's MetricCard has no delta line, sentence or trace control.
 */
export function Stat({
  label,
  value,
  delta,
  text,
  trace,
}: {
  label: string;
  value: string | null;
  delta: string;
  text: string;
  trace: ReactNode;
}) {
  return (
    <article className="group/trace flex min-w-0 flex-col gap-1">
      <div className="flex min-h-7 items-center justify-between gap-2">
        <p className="text-small text-text-tertiary">{label}</p>
        {trace}
      </div>
      <span className="font-body text-h3 font-bold text-text-primary tabular-nums">
        {value === null ? <Missing /> : value}
      </span>
      <span className="text-caption font-medium text-text-secondary">{delta}</span>
      <p className="mt-2 max-w-[60ch] text-small text-text-secondary">{text}</p>
    </article>
  );
}
