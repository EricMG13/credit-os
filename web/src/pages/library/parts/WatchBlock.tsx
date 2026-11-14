import type { RecordBlock } from "../slice";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";

const WORD = { leading: "Leading", lagging: "Lagging" } as const;

/** The mock's two marks: a triangle for an indicator that leads, a square for one that lags. */
function Mark({ timing }: { timing: keyof typeof WORD }) {
  return timing === "leading" ? (
    <span className="h-0 w-0 border-x-[5px] border-b-8 border-x-transparent border-b-current" />
  ) : (
    <span className="size-2.5 rounded-xs border-[1.5px] border-current" />
  );
}

/**
 * Indicators to watch (R8, one static row each): the mark for leading or lagging, named by its word
 * for a screen reader, the indicator, its threshold and one trace control. A legend explains the marks.
 */
export function WatchBlock({ block }: { block: Extract<RecordBlock, { kind: "watch" }> }) {
  return (
    <Section title={block.title} level={SUBSECTION_HEADING}>
      <div>
        <ul>
          {block.items.map((item) => (
            <li
              key={item.indicator}
              className={`${TRACE_HOST} flex flex-wrap items-center gap-1.5 border-b border-border-hairline py-3 text-small last:border-b-0`}
            >
              <span
                role="img"
                aria-label={WORD[item.timing]}
                className="flex size-7 flex-none items-center justify-center rounded-ds-full border border-border-hairline bg-surface-subtle text-text-tertiary"
              >
                <Mark timing={item.timing} />
              </span>
              <span className="min-w-40 flex-1 font-medium text-text-primary">
                {item.indicator}
              </span>
              <span className="text-text-tertiary tabular-nums">{item.threshold}</span>
              <TraceControl trace={item.trace} label="Show sources for this indicator" />
            </li>
          ))}
        </ul>
        <p className="mt-3 flex items-center gap-2 text-small text-text-tertiary">
          <span aria-hidden="true" className="flex">
            <Mark timing="leading" />
          </span>
          {WORD.leading}
          <span aria-hidden="true" className="ml-3 flex">
            <Mark timing="lagging" />
          </span>
          {WORD.lagging}
        </p>
      </div>
    </Section>
  );
}
