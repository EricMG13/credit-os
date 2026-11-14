import { GapPanel } from "@/components/gap/GapPanel";
import { Missing } from "@/components/gap/Missing";
import { Withheld } from "@/components/gap/Withheld";
import type { Cell } from "../slice";

/**
 * A figure as the slice delivered it, in a block: its text in `figureClass` (size, weight,
 * numerals), "n.a." the same size but regular weight, or Withheld or a gap panel in their own
 * type, which never inherits the figure's.
 */
export function CellValue({ cell, figureClass }: { cell: Cell; figureClass: string }) {
  if (cell === null) {
    return (
      <div>
        <span className={`${figureClass} font-normal`}>
          <Missing />
        </span>
      </div>
    );
  }
  switch (cell.kind) {
    case "value":
      return (
        <div>
          <span className={figureClass}>{cell.text}</span>
        </div>
      );
    case "withheld":
      return <div>{cell.reason === null ? <Withheld /> : <Withheld reason={cell.reason} />}</div>;
    case "gap":
      return <GapPanel reason={cell.reason} />;
  }
}
