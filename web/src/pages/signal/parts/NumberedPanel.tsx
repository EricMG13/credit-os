// After the shadcnblocks List Panel, Stacked variant, with a number in the item's media slot (mock
// departure 8: the Numbered variant is behind the source's paid tier, so the marker is drawn here).
// The number is the delivered one. A point may carry a body and `children` (the digest page puts the
// stories behind the point there); `leadAs` sets the lead's tag where the page's headings need it.
import type { ReactNode } from "react";

type Item = { number: string; lead: string; body?: string | null; children?: ReactNode };

export function NumberedPanel({
  items,
  leadAs: Lead = "span",
}: {
  items: Item[];
  leadAs?: "span" | "h3" | "h4";
}) {
  return (
    <ol className="overflow-hidden rounded-md border border-border-hairline bg-surface-card">
      {items.map((item, index) => (
        <li
          key={index}
          className="flex items-start gap-4 p-4 not-first:border-t not-first:border-border-hairline"
        >
          <span
            aria-hidden="true"
            className="grid size-8 shrink-0 place-items-center rounded-xs border border-border-hairline bg-surface-subtle text-sm font-semibold text-text-primary tabular-nums"
          >
            {item.number}
          </span>
          <div className="min-w-0 flex-1">
            <Lead className="text-sm font-medium text-text-primary">{item.lead}</Lead>
            {item.body === undefined || item.body === null ? null : (
              <p className="mt-1 max-w-[72ch] text-sm text-text-tertiary">{item.body}</p>
            )}
            {item.children}
          </div>
        </li>
      ))}
    </ol>
  );
}
