// After the shadcnblocks announcement pill (sources/live-pages.md): the "AI" label badge and one
// line of AI text. AI text is never drawn as a message bubble.
import type { ReactNode } from "react";

export function Announcement({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex max-w-full items-center gap-2 rounded-full border border-border-hairline bg-surface-card py-0.5 pr-3 pl-3 text-xs font-medium text-text-primary shadow-1">
      <span className="-ml-2.5 shrink-0 rounded-full bg-surface-subtle px-2.5 py-1 text-text-secondary">
        AI
      </span>
      <span className="py-1">{children}</span>
    </span>
  );
}
