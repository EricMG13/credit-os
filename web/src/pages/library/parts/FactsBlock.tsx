import { useId } from "react";
import type { RecordBlock } from "../slice";
import { InlineCell } from "./InlineCell";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";
import { TRACE_HOST, TraceControl } from "./TraceControl";

type Group = Extract<RecordBlock, { kind: "facts" }>["groups"][number];

/** One group of terms: its name (when it has one) names the list of rows beneath it. */
function FactGroup({ group }: { group: Group }) {
  const nameId = useId();
  return (
    <>
      {group.name === null ? null : (
        <p id={nameId} className="pt-4 pb-1 text-xs font-medium text-text-tertiary">
          {group.name}
        </p>
      )}
      <dl aria-labelledby={group.name === null ? undefined : nameId}>
        {group.rows.map((row) => (
          <div
            key={row.label}
            className={`${TRACE_HOST} grid grid-cols-3 gap-4 border-b border-border-hairline py-3 text-sm last:border-b-0`}
          >
            <dt className="font-medium text-text-primary">{row.label}</dt>
            <dd className="col-span-2 flex items-center justify-between gap-2 text-text-secondary">
              <InlineCell cell={row.value} />
              <span className="-my-1">
                <TraceControl trace={row.trace} label="Show sources for this fact" />
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </>
  );
}

/** Terms as a details list (R2, the HyperUI look): a name, then a term and its value in each row. */
export function FactsBlock({ block }: { block: Extract<RecordBlock, { kind: "facts" }> }) {
  return (
    <Section title={block.title} level={SUBSECTION_HEADING}>
      <div>
        {block.groups.map((group) => (
          <FactGroup key={group.name ?? ""} group={group} />
        ))}
      </div>
    </Section>
  );
}
