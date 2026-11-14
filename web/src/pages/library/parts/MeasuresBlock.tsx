import type { RecordBlock } from "../slice";
import { Measure } from "./Measure";
import { QuietSection } from "./Section";

/** Measures and their consequence: three stats across from 640px wide, the mock's `mrow`, with no visible heading. */
export function MeasuresBlock({ block }: { block: Extract<RecordBlock, { kind: "measures" }> }) {
  return (
    <QuietSection title={block.title}>
      <ul className="grid grid-cols-1 gap-10 sm:grid-cols-3">
        {block.items.map((item) => (
          <Measure key={item.label} item={item} />
        ))}
      </ul>
    </QuietSection>
  );
}
