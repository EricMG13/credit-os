import { ChevronDown } from "@untitledui/icons";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { RecordBlock } from "../slice";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";

type Question = Extract<RecordBlock, { kind: "questions" }>["items"][number];

const ROW = "flex items-center justify-between gap-4 px-4 py-3 text-body font-medium";

/**
 * One question. With an answer it is a native `details` row (R3, the HyperUI accordion), whose summary
 * the browser opens and closes by pointer, Enter and Space; the answer carries its one trace control.
 * Without one it is a plain row: an expander that opens nothing would be a dead control.
 */
function QuestionRow({ item, open }: { item: Question; open: boolean }) {
  const head = (
    <>
      <span className="flex-1 text-text-primary">{item.question}</span>
      <StatusBadge set="Answer state" state={item.state} />
    </>
  );
  if (item.answer === null) return <div className={ROW}>{head}</div>;
  return (
    <details open={open} className="group">
      <summary
        className={`${ROW} cursor-pointer list-none outline-hidden focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-inset [&::-webkit-details-marker]:hidden`}
      >
        {head}
        <ChevronDown
          aria-hidden="true"
          className="size-4 flex-none text-text-tertiary transition-transform duration-150 group-open:rotate-180 motion-reduce:transition-none"
        />
      </summary>
      <div className={`${TRACE_HOST} flex items-start gap-3 px-4 pt-1 pb-4`}>
        <p className="max-w-[72ch] flex-1 text-body text-text-secondary">{item.answer}</p>
        <TraceControl trace={item.trace} label="Show sources for this answer" />
      </div>
    </details>
  );
}

/** Questions this module set out to answer: an accordion of rows, a state badge on each. */
export function QuestionsBlock({ block }: { block: Extract<RecordBlock, { kind: "questions" }> }) {
  return (
    <Section title={block.title} level={SUBSECTION_HEADING}>
      <ul className="divide-y divide-border-hairline rounded-lg border border-border-hairline bg-surface-card">
        {block.items.map((item, index) => (
          <li key={item.question}>
            <QuestionRow item={item} open={index === 0} />
          </li>
        ))}
      </ul>
    </Section>
  );
}
