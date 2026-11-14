import { useId } from "react";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { Readiness as ReadinessData } from "../slice";

type Group = "Not met" | "Met";

function ItemGroup({ state, count, items }: { state: Group; count: string; items: string[] }) {
  const id = useId();
  return (
    <section className="flex flex-col gap-2 rounded-ds-md bg-surface-subtle p-3">
      <h3 id={id} className="flex items-center gap-2 text-sm font-semibold text-text-primary">
        <StatusBadge set="Met or not met" state={state} /> <span>{count}</span>
      </h3>
      <ul aria-labelledby={id} className="flex flex-col gap-2">
        {items.map((item, i) => (
          <li
            key={`${String(i)}-${item}`}
            className="rounded-ds-md border border-border-hairline bg-surface-card p-2 text-sm font-medium text-text-primary"
          >
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The readiness panel: what the slice says is met and not met, and the spending cap. */
export function Readiness({ data }: { data: ReadinessData }) {
  const titleId = useId();
  return (
    <aside
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-ds-lg border border-border-subtle bg-surface-card p-6 shadow-1"
    >
      <div className="flex flex-col gap-1">
        <h2 id={titleId} className="font-display text-h3 text-text-primary">
          Readiness
        </h2>
        <p className="text-sm text-text-secondary">{data.line}</p>
      </div>
      {data.notMet.items.length > 0 ? (
        <ItemGroup state="Not met" count={data.notMet.count} items={data.notMet.items} />
      ) : null}
      <ItemGroup state="Met" count={data.met.count} items={data.met.items} />
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-text-secondary">Spending cap for this run</p>
        <ProgressBar value={data.cap.value} max={data.cap.max} label={data.cap.label} />
      </div>
    </aside>
  );
}
