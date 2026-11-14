import { GapPanel } from "@/components/gap/GapPanel";
import { Item } from "../parts/Item";
import { PublishedModel } from "../parts/PublishedModel";
import type { ColumnsData, GapItem, Published, StatementsPage } from "../slice/types";
import { ColumnsCard } from "./ColumnsCard";
import { gapReason, pairGrid } from "./shared";

/** Recovery by class and case, with the gap panel, the figure check and the published model. */
export function RecoverySection({
  recovery,
  gap,
  checkFigure,
  published,
}: {
  recovery: ColumnsData;
  gap: GapItem;
  checkFigure: StatementsPage["checkFigure"];
  published: Published | null;
}) {
  return (
    <section className={pairGrid(recovery.series.length + 1)}>
      <ColumnsCard data={recovery} />
      <div className="flex flex-col gap-6">
        <GapPanel reason={gapReason(gap)} />
        <Item
          title={checkFigure.title}
          text={checkFigure.text}
          href={checkFigure.href}
          trace={null}
        />
        <PublishedModel published={published} />
      </div>
    </section>
  );
}
