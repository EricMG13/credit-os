import { InfoCircle } from "@untitledui/icons";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { Missing } from "@/components/gap/Missing";
import { Withheld } from "@/components/gap/Withheld";
import type { Metric } from "../slice/types";
import { TraceControl } from "./TraceControl";

/**
 * One headline figure as its own card: label with its definition, a trace control, then the value
 * and the delivered delta line. A missing value draws "n.a." and a withheld one the kit's Withheld,
 * each with its delivered sentence. Kit need: MetricCard has no delta, trace control or reason.
 */
export function MetricTile({ metric }: { metric: Metric }) {
  const { value } = metric;
  return (
    <article className="group/trace flex min-w-0 flex-col gap-2 rounded-ds-lg border border-border-hairline bg-surface-card p-5 shadow-1">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <p className="text-sm font-medium text-text-tertiary">{metric.label}</p>
          <Tooltip title={metric.definition}>
            <TooltipTrigger
              aria-label={`About ${metric.label}`}
              className="rounded-ds-xs text-text-tertiary focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              <InfoCircle aria-hidden="true" className="size-4" />
            </TooltipTrigger>
          </Tooltip>
        </div>
        {metric.trace === null ? null : (
          <TraceControl href={metric.trace} label={`Show the sources for ${metric.label}`} />
        )}
      </div>
      <div className="flex min-h-[38px] flex-wrap items-end justify-between gap-3">
        {"withheld" in value ? (
          <Withheld reason={metric.note ?? undefined} />
        ) : (
          <>
            <span className="font-body text-h2 tabular-nums text-text-primary">
              {value.text === null ? <Missing /> : value.text}
            </span>
            {metric.delta === null ? null : (
              <span className="inline-flex items-center rounded-ds-sm border border-border-hairline px-2 py-0.5 text-sm font-medium whitespace-nowrap text-text-secondary">
                {metric.delta}
              </span>
            )}
          </>
        )}
      </div>
      {"withheld" in value || metric.note === null ? null : (
        <p className="text-small text-text-tertiary">{metric.note}</p>
      )}
    </article>
  );
}
