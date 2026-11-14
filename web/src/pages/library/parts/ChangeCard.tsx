import { Badge } from "@/components/base/badges/badges";
import type { Change } from "../slice";
import { CellValue } from "./CellValue";
import { InlineCell } from "./InlineCell";
import { TRACE_HOST, TraceControl } from "./TraceControl";

const VALUE = "text-2xl/8 tabular-nums text-text-primary";

const MARKS = {
  // The mock's chevron (ds.css .chev, .chev-u) and its arrow (.arrow), drawn from borders.
  down: "mx-1 mb-[3px] inline-block size-2 flex-none rotate-45 border-r-[1.5px] border-b-[1.5px] border-current",
  up: "mx-1 mt-[3px] inline-block size-2 flex-none -rotate-135 border-r-[1.5px] border-b-[1.5px] border-current",
  flat: "relative mx-1 inline-block h-[1.5px] w-3.5 flex-none bg-current after:absolute after:-top-[3px] after:right-0 after:size-1.5 after:rotate-45 after:border-t-[1.5px] after:border-r-[1.5px] after:border-current after:content-['']",
} as const;

/** The delivered direction: its words and, for up, down or flat, the mock's mark; "none" has no mark. */
function Direction({ change }: { change: Change }) {
  if (change.change === null) return null;
  return (
    <span className="inline-flex items-center gap-2 self-end rounded-ds-xs bg-surface-subtle px-1.5 py-1 text-xs font-medium text-text-secondary">
      {change.direction === "none" ? null : (
        <span
          aria-hidden="true"
          data-direction={change.direction}
          className={MARKS[change.direction]}
        />
      )}
      {change.change}
    </span>
  );
}

/**
 * One change as a card (F3, the stat with its "from" value): the kind and direction on top, the
 * measure, its value with the earlier value beside it, then cause and effect. The mark is the
 * delivered one, never worked out from the figures.
 */
export function ChangeCard({ change }: { change: Change }) {
  return (
    <li
      className={`${TRACE_HOST} flex min-w-0 flex-col gap-4 rounded-lg border border-border-hairline bg-surface-card p-6`}
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <span className="ml-9">
          <Badge size="sm">{change.kind}</Badge>
        </span>
        <Direction change={change} />
      </div>
      <div className="flex flex-col gap-1">
        <strong className="text-small font-medium text-text-tertiary">{change.measure}</strong>
        <div className="flex flex-wrap items-baseline gap-x-1.5">
          <CellValue cell={change.current} figureClass={VALUE} weight="font-medium" />
          <span className="flex items-baseline gap-1 text-xs text-text-tertiary">
            from <InlineCell cell={change.from} />
          </span>
        </div>
      </div>
      <p className="border-t border-border-hairline pt-3 text-small text-text-secondary">
        <span className="font-semibold text-text-primary">{change.cause}</span> {change.effect}
      </p>
      <span className="absolute top-5 left-5">
        <TraceControl trace={change.trace} label="Show sources for this change" />
      </span>
    </li>
  );
}
