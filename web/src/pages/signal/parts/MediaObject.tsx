// After sources/hui/media-1.html: a media tile on the left, the content beside it, aligned to the
// top. The tile is 80px as the mock draws it (mock question 10); it holds the publication's monogram.
import type { ReactNode } from "react";

export function MediaObject({ tile, children }: { tile: string; children: ReactNode }) {
  return (
    <div className="flex items-start gap-4">
      <span
        aria-hidden="true"
        className="flex size-20 shrink-0 items-center justify-center rounded bg-surface-subtle font-display text-h2 text-text-secondary"
      >
        {tile}
      </span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
