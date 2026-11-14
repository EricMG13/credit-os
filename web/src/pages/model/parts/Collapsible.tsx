import type { ReactNode } from "react";

/** A native `details` card, open by default: Enter and Space on its summary fold it. */
export function Collapsible({
  summary,
  open = true,
  children,
}: {
  summary: ReactNode;
  /** Whether it starts open; the reader folds and unfolds it from there. */
  open?: boolean;
  children: ReactNode;
}) {
  return (
    <details
      open={open}
      className="group/clp rounded-ds-sm border border-border-hairline bg-surface-card"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-body font-medium text-text-primary outline-focus focus-visible:outline-2 focus-visible:outline-offset-2 [&::-webkit-details-marker]:hidden">
        {summary}
        <span
          aria-hidden="true"
          className="mr-1 ml-auto size-[7px] rotate-45 border-r-[1.5px] border-b-[1.5px] border-current transition-transform duration-150 group-open/clp:-rotate-[135deg] motion-reduce:transition-none"
        />
      </summary>
      <div className="flex max-w-[90ch] flex-col gap-2 px-4 pt-1 pb-4 text-small text-text-secondary">
        {children}
      </div>
    </details>
  );
}
