// Follows the HyperUI stats examples "Title, value and icon" (without the icon) and the first
// example's "from" value (without the growth badge).
import { InfoCircle } from "@untitledui/icons";
import { Missing } from "@/components/gap/Missing";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";

interface MetricCardProps {
  label: string;
  /** The display string, formatted by the caller; null when the figure is missing. */
  value: string | null;
  /** The previous value, same form; null when missing; omitted when there is none to show. */
  from?: string | null;
  /** The metric's definition, shown in a tooltip on an info trigger. */
  note?: string;
}

export function MetricCard({ label, value, from, note }: MetricCardProps) {
  return (
    <article className="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-card p-6">
      <div className="flex items-center gap-1.5">
        <p className="text-sm text-text-tertiary">{label}</p>
        {note !== undefined && (
          <Tooltip title={note}>
            <TooltipTrigger
              aria-label={`About ${label}`}
              className="rounded-ds-xs text-text-tertiary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              <InfoCircle aria-hidden="true" className="size-4" />
            </TooltipTrigger>
          </Tooltip>
        )}
      </div>
      <p>
        <span className="text-2xl font-medium tabular-nums text-text-primary">
          {value === null ? <Missing /> : value}
        </span>
        {from !== undefined && (
          <span className="ml-2 text-xs tabular-nums text-text-tertiary">
            from {from === null ? <Missing /> : from}
          </span>
        )}
      </p>
    </article>
  );
}
