import type { RecordBlock } from "../slice";
import { ChartTableBlock } from "./ChartTableBlock";
import { EdgesBlock } from "./EdgesBlock";
import { FactsBlock } from "./FactsBlock";
import { MatrixBlock } from "./MatrixBlock";
import { MeasuresBlock } from "./MeasuresBlock";
import { MetricsBlock } from "./MetricsBlock";
import { GapBlock } from "./GapBlock";
import { QuestionsBlock } from "./QuestionsBlock";
import { StatementBlock } from "./StatementBlock";
import { StatusBlock } from "./StatusBlock";
import { WatchBlock } from "./WatchBlock";
import { recordSections } from "./recordNav";

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
    case "metrics":
      return <MetricsBlock block={block} />;
    case "measures":
      return <MeasuresBlock block={block} />;
    case "facts":
      return <FactsBlock block={block} />;
    case "status":
      return <StatusBlock block={block} />;
    case "statement":
      return <StatementBlock block={block} />;
    case "chartTable":
      return <ChartTableBlock block={block} />;
    case "gap":
      return <GapBlock block={block} />;
  }
}

/** What a block is set beside: a chart table is named by its chart. */
type Kind =
  | Exclude<RecordBlock["kind"], "chartTable">
  | Extract<RecordBlock, { kind: "chartTable" }>["chart"];
const kindOf = (block: RecordBlock): Kind =>
  block.kind === "chartTable" ? block.chart : block.kind;

/** The mock sets some blocks side by side: the watch list with the questions, the terms with the tests, the peer scatter with the peer range. */
const BESIDE: Partial<Record<Kind, Kind>> = {
  watch: "questions",
  facts: "status",
  scatter: "range",
};

/**
 * A pair's grid, two-up from 1200px for every pair, so each half has room (side by side at 1440px,
 * stacked at 1024px): the mock's 40px gap, and for two chart tables its 24px gap.
 */
const PAIR: Partial<Record<Kind, string>> = {
  scatter: "grid grid-cols-1 gap-6 min-[1200px]:grid-cols-2",
};
const PAIR_DEFAULT = "grid grid-cols-1 gap-10 min-[1200px]:grid-cols-2";

/** Two adjacent blocks of a pair share a row. */
function rows(blocks: readonly RecordBlock[]): RecordBlock[][] {
  const out: RecordBlock[][] = [];
  for (const block of blocks) {
    const last = out.at(-1);
    const first = last?.[0];
    if (last?.length === 1 && first !== undefined && BESIDE[kindOf(first)] === kindOf(block)) {
      last.push(block);
    } else {
      out.push([block]);
    }
  }
  return out;
}

/**
 * A module's record blocks, in the order the module delivered them. The first block of each
 * navigator entry is the target that entry scrolls to; its heading takes focus.
 */
export function Records({ blocks }: { blocks: readonly RecordBlock[] }) {
  const sections = recordSections(blocks);
  return (
    <div className="flex flex-col gap-10">
      {rows(blocks).map((row) => (
        <div
          key={row.map((block) => block.title).join("|")}
          className={
            row.length === 2 ? (PAIR[kindOf(row[0] as RecordBlock)] ?? PAIR_DEFAULT) : undefined
          }
        >
          {row.map((block) => {
            const target = sections.find((section) => section.first === block);
            return target === undefined ? (
              <Block key={block.title} block={block} />
            ) : (
              <div key={block.title} data-section={target.key} className="scroll-mt-6">
                <Block block={block} />
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
