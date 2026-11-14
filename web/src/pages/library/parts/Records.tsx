import type { RecordBlock } from "../slice";
import { EdgesBlock } from "./EdgesBlock";
import { MatrixBlock } from "./MatrixBlock";
import { QuestionsBlock } from "./QuestionsBlock";
import { WatchBlock } from "./WatchBlock";

function Block({ block }: { block: RecordBlock }) {
  switch (block.kind) {
    case "matrix":
      return <MatrixBlock block={block} />;
    case "watch":
      return <WatchBlock block={block} />;
    case "questions":
      return <QuestionsBlock block={block} />;
    case "edges":
      return <EdgesBlock block={block} />;
  }
}

/** The mock sets the watch list and the questions side by side: two adjacent blocks of those kinds share a row. */
function rows(blocks: readonly RecordBlock[]): RecordBlock[][] {
  const out: RecordBlock[][] = [];
  for (const block of blocks) {
    const last = out.at(-1);
    if (block.kind === "questions" && last?.length === 1 && last[0]?.kind === "watch") {
      last.push(block);
    } else {
      out.push([block]);
    }
  }
  return out;
}

/** A module's record blocks, in the order the module delivered them, under one navigator entry. */
export function Records({ blocks }: { blocks: readonly RecordBlock[] }) {
  return (
    <div className="flex flex-col gap-10">
      {rows(blocks).map((row) => (
        <div
          key={row.map((block) => block.title).join("|")}
          className={
            row.length === 2 ? "grid grid-cols-1 gap-10 min-[1001px]:grid-cols-2" : undefined
          }
        >
          {row.map((block) => (
            <Block key={block.title} block={block} />
          ))}
        </div>
      ))}
    </div>
  );
}
