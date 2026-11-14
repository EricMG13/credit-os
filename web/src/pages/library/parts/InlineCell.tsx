import { Missing } from "@/components/gap/Missing";
import { Withheld } from "@/components/gap/Withheld";
import { GapBadge } from "@/components/status/StatusBadge";
import type { Cell } from "../slice";

/** A figure inside a line of text: its text as delivered, "n.a." when missing, or the inline withheld and gap forms. */
export function InlineCell({ cell }: { cell: Cell }) {
  if (cell === null) return <Missing />;
  switch (cell.kind) {
    case "value":
      return <span className="tabular-nums">{cell.text}</span>;
    case "withheld":
      return cell.reason === null ? <Withheld /> : <Withheld reason={cell.reason} />;
    case "gap":
      return <GapBadge />;
  }
}
