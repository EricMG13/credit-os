import type { RecordBlock } from "../slice";
import { MatrixBlock } from "./MatrixBlock";

/** A module's record blocks, in the order the module delivered them, under one navigator entry. */
export function Records({ blocks }: { blocks: readonly RecordBlock[] }) {
  return (
    <div className="flex flex-col gap-10">
      {blocks.map((block) => (
        <MatrixBlock key={block.title} block={block} />
      ))}
    </div>
  );
}
