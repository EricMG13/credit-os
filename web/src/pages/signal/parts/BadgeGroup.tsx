// After sources/uui/badge-groups.tsx (mock departure 6): badge, arrow, badge, then the word, all
// neutral. The source's order is badge, text, arrow; direction is carried by the word, never a colour.
// Read aloud as one phrase: "<from> to <to>, <word>"; the arrow is decorative.
import { ArrowRight } from "@untitledui/icons";

const BADGE =
  "rounded-full bg-surface-card px-2.5 py-0.5 font-medium text-text-primary tabular-nums ring-1 ring-border-hairline ring-inset";

export function BadgeGroup({ from, to, word }: { from: string; to: string; word: string }) {
  return (
    <span
      role="img"
      aria-label={`${from} to ${to}, ${word}`}
      className="inline-flex items-center gap-1.5 rounded-full bg-surface-subtle p-1 text-sm font-medium text-text-secondary ring-1 ring-border-hairline ring-inset"
    >
      <b aria-hidden="true" className={BADGE}>
        {from}
      </b>
      <ArrowRight aria-hidden="true" className="size-4 text-fg-quaternary" />
      <b aria-hidden="true" className={BADGE}>
        {to}
      </b>
      <span aria-hidden="true" className="pr-2">
        {word}
      </span>
    </span>
  );
}
