import { GapPanel } from "@/components/gap/GapPanel";
import type { RecordBlock } from "../slice";
import { Section } from "./Section";
import { SUBSECTION_HEADING } from "./heading";

/** What the module could not establish, in the kit's gap panel with the module's own reason. */
export function GapBlock({ block }: { block: Extract<RecordBlock, { kind: "gap" }> }) {
  return (
    <Section title={block.title} level={SUBSECTION_HEADING}>
      <GapPanel reason={block.reason} />
    </Section>
  );
}
