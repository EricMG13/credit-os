import { useId } from "react";
import { StatusBadge } from "@/components/status/StatusBadge";
import type { RecordBlock } from "../slice";
import { InlineCell } from "./InlineCell";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TraceControl } from "./TraceControl";

type Group = Extract<RecordBlock, { kind: "status" }>["groups"][number];

/** One group, in its state's word and shape, with the delivered count: a band, then a card for each test. */
function TestGroup({ group }: { group: Group }) {
  const headId = useId();
  return (
    <div
      role="group"
      aria-labelledby={headId}
      className="overflow-hidden rounded-lg bg-surface-subtle"
    >
      <div id={headId} className="flex items-center gap-2 bg-border-strong/5 p-3">
        <StatusBadge set="Met or not met" state={group.state} />
        <span className="rounded-ds-full bg-surface-subtle px-2 py-0.5 text-xs font-medium text-text-secondary tabular-nums ring-1 ring-border-hairline ring-inset">
          {group.count}
        </span>
      </div>
      <ul className="flex flex-col gap-2 p-3">
        {group.items.map((item) => (
          <li
            key={item.text}
            className="group/trace relative flex flex-wrap items-center gap-2 rounded-lg border border-border-hairline bg-surface-card p-2 text-sm font-medium text-text-primary shadow-xs"
          >
            {item.text}
            <div className="ml-auto flex items-center gap-2 font-normal text-text-secondary tabular-nums">
              <InlineCell cell={item.value} />
              <TraceControl trace={item.trace} label="Show sources for this test" />
            </div>
            {item.note === null ? null : (
              <p className="basis-full text-xs font-normal text-text-tertiary">{item.note}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tests met or not met (R6): a list for each state, in the order delivered, the state never by colour alone. */
export function StatusBlock({ block }: { block: Extract<RecordBlock, { kind: "status" }> }) {
  return (
    <Section title={block.title} level={SUBSECTION_HEADING}>
      <div className="flex flex-col gap-3">
        {block.groups.map((group) => (
          <TestGroup key={group.state} group={group} />
        ))}
      </div>
    </Section>
  );
}
