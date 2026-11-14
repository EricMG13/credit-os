import { useContext } from "react";
import { Tooltip, TooltipTrigger } from "@/components/base/tooltip/tooltip";
import { RunContext } from "./RunContext";

/** Put on the element that holds a control, so hovering the figure reveals it. */
export const TRACE_HOST = "group/trace relative";

/**
 * The one trace control per paragraph, row or figure. Hidden at rest; shown on hover of its host,
 * on keyboard focus, always on touch, and for every control while the frame's Show sources is on.
 * `null` is a figure with no trace: it draws nothing.
 */
export function TraceControl({ trace }: { trace: string | null }) {
  const run = useContext(RunContext);
  if (run === null) throw new Error("TraceControl was drawn outside a RunFrame");
  if (trace === null) return null;
  if (!Object.hasOwn(run.traces, trace)) {
    throw new RangeError(`the run holds no trace "${trace}"`);
  }
  return (
    <Tooltip title="Show sources" placement="top right">
      <TooltipTrigger
        aria-label="Show sources for this figure"
        onPress={() => {
          run.open(trace);
        }}
        className="flex size-7 flex-none cursor-pointer items-center justify-center rounded-ds-sm border border-border-hairline bg-surface-card text-text-tertiary opacity-0 transition-opacity duration-150 group-hover/trace:opacity-100 hover:border-action-subtle-hover hover:bg-action-subtle hover:text-action focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 in-data-[sources=on]:opacity-100 motion-reduce:transition-none [@media(hover:none)]:opacity-100"
      >
        <span
          aria-hidden="true"
          className="relative size-2.5 rounded-ds-full border-[1.5px] border-current"
        >
          <span className="absolute inset-0.5 rounded-ds-full bg-current" />
        </span>
      </TooltipTrigger>
    </Tooltip>
  );
}
