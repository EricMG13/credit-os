import { GapPanel } from "@/components/gap/GapPanel";
import { Missing } from "@/components/gap/Missing";
import { Withheld } from "@/components/gap/Withheld";
import type { Cell } from "../slice";

/** A figure as the slice delivered it: its text, "n.a." when missing, Withheld, or a gap panel. */
export function CellValue({ cell }: { cell: Cell }) {
  if (cell === null) return <Missing />;
  switch (cell.kind) {
    case "value":
      return <>{cell.text}</>;
    case "withheld":
      return cell.reason === null ? <Withheld /> : <Withheld reason={cell.reason} />;
    case "gap":
      return <GapPanel reason={cell.reason} />;
  }
}
