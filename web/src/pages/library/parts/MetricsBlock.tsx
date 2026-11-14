import type { RecordBlock } from "../slice";
import { MetricTile } from "./MetricTile";
import { QuietSection } from "./Section";

/** The module's headline figures: three tiles across from 640px wide, the mock's row, with no visible heading. */
export function MetricsBlock({ block }: { block: Extract<RecordBlock, { kind: "metrics" }> }) {
  return (
    <QuietSection title={block.title}>
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {block.items.map((metric) => (
          <MetricTile key={metric.label} metric={metric} />
        ))}
      </ul>
    </QuietSection>
  );
}
