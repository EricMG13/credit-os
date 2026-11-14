import type { RecordBlock } from "../slice";
import { CellValue } from "./CellValue";
import { DirectionMark } from "./DirectionMark";
import { InlineCell } from "./InlineCell";
import { TRACE_HOST, TraceControl } from "./TraceControl";

type Item = Extract<RecordBlock, { kind: "measures" }>["items"][number];

const FIGURE = "text-2xl/8 tracking-[-0.025em] tabular-nums text-text-primary";

/**
 * One measure as a stat with its consequence (F2): the figure, a line that is the delivered change
 * with its mark or, when there is none, the earlier period itself (n.a. when it is missing), then
 * what it means. The mark is the delivered direction; nothing is worked out from the figures.
 */
export function Measure({ item }: { item: Item }) {
  return (
    <li className={`${TRACE_HOST} flex min-w-0 flex-col gap-1`}>
      <span className="pr-9 text-sm text-text-tertiary">{item.label}</span>
      <CellValue cell={item.current} figureClass={FIGURE} />
      <span className="flex items-center gap-1 text-xs font-medium text-text-secondary">
        {item.delta === null ? (
          <>
            Earlier period <InlineCell cell={item.earlier} />
          </>
        ) : (
          <>
            <DirectionMark direction={item.delta.direction} />
            {item.delta.text}
          </>
        )}
      </span>
      <span className="mt-1 text-sm/[21px] text-text-secondary">{item.consequence}</span>
      <span className="absolute top-0 right-0">
        <TraceControl trace={item.trace} label="Show sources for this measure" />
      </span>
    </li>
  );
}
