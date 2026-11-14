import type { RecordBlock } from "../slice";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";

/**
 * A pathway (R5): the steps in order in one bordered row from 901px wide, stacked below. The kit's
 * ProgressSteps is a run's progress with complete and current states and a line through titles, not
 * this look, so the mock's own is drawn. Steps are numbered by the list counter, not by a figure the
 * page makes, and carry no trace control: the module delivers none for them.
 */
export function EdgesBlock({ block }: { block: Extract<RecordBlock, { kind: "edges" }> }) {
  return (
    <Section title={block.title} level={SUBSECTION_HEADING}>
      <ol className="grid grid-cols-1 overflow-hidden rounded-lg border border-border-hairline text-small text-text-secondary [counter-reset:step] min-[901px]:grid-flow-col min-[901px]:auto-cols-fr">
        {block.steps.map((step) => (
          <li
            key={step.title}
            className="flex items-center gap-2 border-t border-border-hairline p-4 [counter-increment:step] first:border-t-0 min-[901px]:justify-center min-[901px]:border-t-0 min-[901px]:border-l min-[901px]:first:border-l-0"
          >
            <span
              aria-hidden="true"
              className="flex size-7 flex-none items-center justify-center rounded-ds-full border-[1.5px] border-current text-caption after:content-[counter(step)]"
            />
            <p>
              <strong className="block font-medium text-text-primary">{step.title}</strong>
              <small className="mt-1 block text-caption">{step.text}</small>
            </p>
          </li>
        ))}
      </ol>
    </Section>
  );
}
