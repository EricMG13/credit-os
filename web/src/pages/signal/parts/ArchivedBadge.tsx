// A thread's archived state (mock departure 14): the neutral badge with the "settled" square. The
// kit's status sets hold no "Archived" word, so it is composed here from the kit's badge and the
// square shape of the "Signal source states" set (Approved: square, neutral).
import type { ReactNode } from "react";
import { Badge } from "@/components/base/badges/badges";
import { STATUS_SETS } from "@/components/status/sets";
import { StatusShape } from "@/components/status/shapes";

export function ArchivedBadge({ children = "Archived" }: { children?: ReactNode }) {
  const { shape } = STATUS_SETS["Signal source states"].Approved;
  return (
    <Badge
      color="gray"
      className="gap-1.5 pl-2"
      icon={
        <span className="inline-flex rounded-ds-full">
          <StatusShape shape={shape} />
        </span>
      }
    >
      {children}
    </Badge>
  );
}
